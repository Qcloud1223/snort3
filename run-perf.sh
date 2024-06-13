#!/bin/bash

# a script to run snort under perf mode
# may also run as a sub-task of run-experiment.sh

set -e

event_list=()
event_set=()
vanilla=false
available_cpus=(
    41
    43
    45
    47
)

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s|--event-set) event_set+=("$2"); shift; shift;;
        -e|--event) event_list+=("$2"); shift; shift;;
        -b|--daq-batch-size) batch_size="$2"; shift; shift;;
        -t|--trace) trace="$2"; shift; shift;;
        -v|--vanilla) vanilla=true; shift;;
        -c|--cpu) pinned_cpu="$2"; shift; shift;;
        *) echo "bad argument $1"; exit 1;;
    esac
done

if [[ -z $trace ]]; then
    echo "No trace specified, exit"
    exit 1
fi

if [[ -z $batch_size ]]; then
    echo "No batch size specified, default to 64"
    batch_size=64
fi

if [[ ${#event_set[@]} == 0 ]]; then
    echo "No event set specified, default to bound"
    event_set+=("bound")
fi

if [[ $vanilla == "true" ]]; then
    path="/home/iom/snort3-vanilla/"
else
    path="/home/iom/snort3-git/"
fi

if [[ -z $pinned_cpu ]]; then
    echo "No cpu specified, default to first available"
    pinned_cpu=${available_cpus[0]}
elif [ "$pinned_cpu" -eq "$pinned_cpu" ] 2>/dev/null
then
    cpu_idx=$(( pinned_cpu % ${#available_cpus[@]} ))
    pinned_cpu=$(( available_cpus[cpu_idx] ))
    # echo "CPU index at ${pinned_cpu}"
else
    echo "a numeric index must be specified!"
    exit 1
fi

for set in "${event_set[@]}"
do
    if [ "$set" == "bound" ]; then
        event_list+=("idq_uops_not_delivered.core:u")
        # identify frontend latency and bandwidth
        event_list+=("idq_uops_not_delivered.cycles_0_uops_deliv.core:u")
        event_list+=("uops_retired.retire_slots:u")
        event_list+=("uops_issued.any:u")
        event_list+=("cpu_clk_unhalted.thread_any:u")
    elif [ "$set" == "backend" ]; then
        event_list+=("cycle_activity.stalls_mem_any:u")
        event_list+=("exe_activity.bound_on_stores:u")
        event_list+=("exe_activity.exe_bound_0_ports:u")
        event_list+=("exe_activity.1_ports_util:u")
    elif [ "$set" == "L1i" ]; then
        event_list+=("L1-icache-misses:u")
    elif [ "$set" == "L1d" ]; then
        event_list+=("L1-dcache-misses:u")
    elif [ "$set" == "LLC-load" ]; then
        event_list+=("LLC-load:u")
        event_list+=("LLC-load-misses:u")
    elif [ "$set" == "LLC-store" ]; then
        event_list+=("LLC-store:u")
        event_list+=("LLC-store-misses:u")
    else
        echo "bad set type $set, exit"
        exit 1
    fi
done

# fun fact: the fd in shell is not visible in script
if [[ -z $ctl_fd ]]; then
    exec {ctl_fd}<>"$path"ctl_fd.fifo
    echo "Setting CTL_FD to ${ctl_fd}"
fi

if [[ -z $ctl_fd_ack ]]; then
    exec {ctl_fd_ack}<>"$path"ctl_fd_ack.fifo
    echo "Setting CTL_FD_ACK to ${ctl_fd_ack}"
fi

event=""
event_count=$((0))

for e in "${event_list[@]}"
do
    event+="$e,"
    event_count=$((event_count+1))
done

# remove trailing comma
real_size=$(( ${#event}-1 ))
event=${event:0:real_size}

# echo taskset -c "$pinned_cpu" perf stat --delay=-1 --control fd:"${ctl_fd}","${ctl_fd_ack}" -B -e "$event" -- "$path"snort/bin/snort -c "$path"lua/snort.lua -r "$trace" -A alert_full --daq-batch-size="$batch_size"
PERF_CTL_FD=$ctl_fd PERF_CTL_ACK_FD=$ctl_fd_ack taskset -c "$pinned_cpu" perf stat --delay=-1 --control fd:"${ctl_fd}","${ctl_fd_ack}" -B -e "$event" -- "$path"snort/bin/snort -c "$path"lua/snort.lua -r "$trace" -A alert_full --daq-batch-size="$batch_size"

if [[ $event_count -gt 8 ]]; then
    echo "Warning: event number over 8, multiplexing might happen and lead to imprecise result"
fi