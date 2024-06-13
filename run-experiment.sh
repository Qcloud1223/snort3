#!/bin/bash

# run experiments multiple times

set -e

trace_list=(
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_2.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_3.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_5.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_10.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_concat_5.pcap"
    "/home/iom/snort3-git/isp_isolated_http_request_dedup_-1_concat_50.pcap"
    # 7
    "/home/iom/snort3-git/test_trace/align_f100_r64_sorted.pcap"
    "/home/iom/snort3-git/test_trace/align_f1000_r64_sorted.pcap"
    "/home/iom/snort3-git/test_trace/align_f10000_r64_sorted.pcap"
    # 10
    "/home/iom/snort3-git/test_trace/align_f10_r4096_sorted.pcap"
    "/home/iom/snort3-git/test_trace/align_f100_r4096_sorted.pcap"
    "/home/iom/snort3-git/test_trace/align_f1000_r4096_sorted.pcap"
    # 13
    "/home/iom/snort3-git/test_trace/align_f10_r65536_sorted.pcap"
    # 14
    "/home/iom/snort3-git/test_trace/align_f10_r131072_sorted.pcap"
    # 15
    "/home/iom/snort3-git/test_trace/align_f10_r262144_sorted.pcap"
    # 16
    "/home/iom/snort3-git/test_trace/align_f10_r524288_sorted.pcap"
)

batch_sizes=(
    1
    2
    4
    8
    16
    32
    64
)

# TODO: check why we cannot use this to run commands?
# filter="2>&1 | sed -E '/^ *[0-9,]+      [0-9a-zA-Z_\.\:-]+/!d' | awk '{print \$1,\$2}'"

while [[ "$#" -gt 0 ]]; do
    case $1 in 
        -r|--repeat) repeat="$2"; shift; shift;;
        -s|--start) start_idx="$2"; shift; shift;;
        -e|--end) trace_length="$2"; shift; shift;;
        *) echo "bad argument $1"; exit 1;;
    esac
done

if [[ -z $repeat ]]; then
    echo "repeat time not set, default to 5" >&2
    repeat=$((5))
fi

if [[ -z $start_idx ]]; then
    echo "start index is not set, in this case end index is ignored"
    echo "setting trace to run 64 flow experiments"
    start_idx=$((7))
    trace_length=$((3))
fi

# run each set of experiment on a different core to prevent stressing certain core
cpu_idx=$((0))

# for every trace
for trace in "${trace_list[@]:start_idx:trace_length}"
do
    echo "----------"
    echo "trace: $trace"
    # for every batch size
    for size in "${batch_sizes[@]}"
    do
        # know when we start this batch, so that I won't get too anxious
        echo -n "// "
        date
        echo "batch size: $size"
        END=$repeat
        # run the optimized version several times
        echo "Optimized:"
        for (( i=0;i<END;i++ )); do
            # echo "CPU index: $cpu_idx"
            # first, we get bound and L1
            ./run-perf.sh -s bound -s L1i -s L1d -t "$trace" -b "$size" -c "$cpu_idx" 2>&1 | sed -E '/^ *[0-9,]+      [0-9a-zA-Z_\.\:-]+/!d' | awk '{print $1,$2}'
            # then, we get L2 and LLC
            ./run-perf.sh -s LLC-load -s LLC-store -t "$trace" -b "$size" -c "$cpu_idx" 2>&1 | sed -E '/^ *[0-9,]+      [0-9a-zA-Z_\.\:-]+/!d' | awk '{print $1,$2}'
            echo ""
            cpu_idx=$((cpu_idx + 1)) 
        done

        # run the vanilla version several times
        echo "Vanilla:"
        for (( i=0;i<END;i++ )); do
            # echo "CPU index: $cpu_idx"
            ./run-perf.sh -s bound -s L1i -s L1d -t "$trace" -b "$size" -c "$cpu_idx" -v 2>&1 | sed -E '/^ *[0-9,]+      [0-9a-zA-Z_\.\:-]+/!d' | awk '{print $1,$2}'
            ./run-perf.sh -s LLC-load -s LLC-store -t "$trace" -b "$size" -c "$cpu_idx" -v 2>&1 | sed -E '/^ *[0-9,]+      [0-9a-zA-Z_\.\:-]+/!d' | awk '{print $1,$2}'
            echo ""
            cpu_idx=$((cpu_idx + 1)) 
        done

        echo ""
        echo ""
    done
done
