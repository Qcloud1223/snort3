import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import sys
import re

if len(sys.argv) < 2:
    print("usage: python plot_expr_new.py trace_name <normalized>")
    exit(-1)
else:
    data_path = sys.argv[1]
normalized = True if len(sys.argv) >= 3 else False

printable_counters = [
    "idq_uops_not_delivered.core:u",
    "uops_retired.retire_slots:u",
    "uops_issued.any:u",
    "cpu_clk_unhalted.thread_any:u",
    "L1-icache-misses",
    "L1-dcache-misses",
    "LLC-load",
    "LLC-load-misses",
    "LLC-store",
    "LLC-store-misses",
    "tsc_cycles",
    "icache_64b.iftag_stall:u",
    "icache_16b.ifdata_stall:u",
    "iicache_16b.ifdata_stall:c1:e1:u",
    "int_misc.clear_resteer_cycles:u",
    "iTLB-load",
    "iTLB-load-misses",
    "dTLB-load",
    "dTLB-load-misses"
]

unprintable_counters = [
    "idq_uops_not_delivered.cycles_0_uops_deliv.core:u"
]

def parse_data(f):
    # lines = f.readlines().strip().split('\n')
    batches = []
    traces = []
    collect_counters = True
    counters_printable = []
    counters_unprintable = []
    # all_batch_data = []
    # all_trace_data = []
    optimized_printable = []
    optimized_unprintable = []
    vanilla_printable = []
    vanilla_unprintable = []
    current_printable_data = []
    current_unprintable_data = []
    
    for line in f.readlines():
        line = line.strip()
        if line.startswith("batch size:"):
            batches.append(int(line.split(":")[1].strip()))
            # all_trace_data[-1].append([])
            optimized_printable[-1].append([])
            optimized_unprintable[-1].append([])
            vanilla_printable[-1].append([])
            vanilla_unprintable[-1].append([])
        elif line.startswith("trace:"):
            traces.append(line.split(":")[1].strip().split('/')[-1])
            # all_trace_data.append([])
            optimized_printable.append([])
            optimized_unprintable.append([])
            vanilla_printable.append([])
            vanilla_unprintable.append([])
        elif line in ["Optimized:", "Vanilla:"]:
            if line.startswith("Optimized"):
                printable_to_write = optimized_printable
                unprintable_to_write = optimized_unprintable
            else:
                printable_to_write = vanilla_printable
                unprintable_to_write = vanilla_unprintable
        # line break note us to push current sample 
        elif not line:
            # and also note we at least collect 1 sample
            collect_counters = False
            if len(current_printable_data) != 0:
                printable_to_write[-1][-1].append(tuple(current_printable_data))
                current_printable_data = []
            if len(current_unprintable_data) != 0:
                unprintable_to_write[-1][-1].append(tuple(current_unprintable_data))
                current_unprintable_data = []
        elif line.startswith('-'):
            batches = []
        elif line.startswith('//'):
            continue
        else:
            if line.split()[1] in printable_counters:
                current_printable_data.append(int(line.split()[0].replace(',', '')))
                if collect_counters == True: counters_printable.append(line.split()[1])
            elif line.split()[1] in unprintable_counters:
                current_unprintable_data.append(int(line.split()[0].replace(',', '')))
                if collect_counters == True: counters_unprintable.append(line.split()[1])
    
    return optimized_printable, optimized_unprintable, vanilla_printable, vanilla_unprintable, traces, batches, counters_printable, counters_unprintable

# Parse the provided data
with open(data_path) as f:
    optimized_printable, optimized_unprintable, vanilla_printable, vanilla_unprintable, traces, batches, counters_printable, counters_unprintable = parse_data(f)

# print(optimized_data)

num_series = len(counters_printable)
num_batches = len(batches)
num_traces = len(traces)
num_repeats = len(optimized_printable[0][0])

print(f"num_series: {num_series}, num_batches: {num_batches}, num_traces: {num_traces}, num_repeats: {num_repeats}")

# get the request number of each trace
trace_reqs = []
if normalized == True:
    for t in traces:
        # assume trace follows format 'XXX_f%d_XXX.txt'
        try:
            request_cnt = int(t.split('f')[-1].split('_')[0])
        except ValueError:
            print(f"Normalizing trace name: {t}, but it does not conform to format?")
            exit(-1)
        trace_reqs.append(request_cnt)

optimized_np = np.array(optimized_printable)
vanilla_np = np.array(vanilla_printable)

# Prepare the figure and axis
fig, axs = plt.subplots(num_series, num_traces, figsize=(24, 24))

# convert the ax into 2d array for later indicing
# note that subplots will not return array of axes if the dimension is 1
# FIXME
if num_traces == 1:
    axs = np.atleast_2d(axs)
    axs = np.transpose(axs)

x_axis = np.arange(len(batches))
# batches = np.array(batches)
opt_bars = np.ndarray(shape=(num_series, num_traces, num_batches), dtype=matplotlib.patches.Rectangle)
# van_bars = np.array((num_series, num_traces, num_batches))

for i in range(num_series):
    ymax = 0
    for j in range(num_traces):
        # batch_data = np.zeros(num_batches)
        batch_opt_mean = np.zeros(num_batches)
        batch_opt_std = np.zeros(num_batches)
        batch_opt_yerr = np.zeros((2,num_batches))
        batch_van_mean = np.zeros(num_batches)
        batch_van_std = np.zeros(num_batches)
        batch_van_yerr = np.zeros((2,num_batches))

        for k in range(num_batches):
            # print(f"i: {i}, j: {j}, k:{k}")
            opt_data = optimized_np[j, k, :, i].astype(float)
            opt_mean = opt_data.mean()
            opt_std  = opt_data.std()
            batch_opt_mean[k] = opt_mean
            batch_opt_std[k] = opt_std
            batch_opt_yerr[0,k] = (opt_mean-min(opt_data)) / (trace_reqs[j] if normalized == True else 1)
            batch_opt_yerr[1,k] = (max(opt_data)-opt_mean) / (trace_reqs[j] if normalized == True else 1)
            ymax = max(ymax, max(opt_data) / trace_reqs[j] if normalized == True else 1)

            van_data = vanilla_np[j, k, :, i].astype(float)
            van_mean = van_data.mean()
            van_std  = van_data.std()
            batch_van_mean[k] = van_mean
            batch_van_std[k] = van_std
            batch_van_yerr[0,k] = (van_mean-min(van_data)) / (trace_reqs[j] if normalized == True else 1)
            batch_van_yerr[1,k] = (max(van_data)-van_mean) / (trace_reqs[j] if normalized == True else 1)
            ymax = max(ymax, max(van_data) / trace_reqs[j] if normalized == True else 1)

        opt_bars[i, j] = axs[i, j].bar(x_axis-0.2, batch_opt_mean / (trace_reqs[j] if normalized == True else 1), color='red', width=0.4, yerr=batch_opt_yerr)    
        axs[i, j].bar(x_axis+0.2, batch_van_mean / (trace_reqs[j] if normalized == True else 1), color='blue', width=0.4, yerr=batch_van_yerr)        
        axs[i, j].set_xticks(x_axis, batches)
        
    if normalized == True:
        for j in range(num_traces):
            axs[i, j].set_ylim(0, ymax*1.1)
            # axs[i, j].set_title(f'Trace: {j}, counter: {i}')
            # axs[i, j].set_xlabel('batch size')
            # axs[i, j].set_ylabel('counts')

# print convert percentage
fe_reduce = np.mean(vanilla_np[:, :, :, 0].astype(float) - optimized_np[:, :, :, 0].astype(float), axis=2)
retire_increase = np.mean(optimized_np[:, :, :, 1].astype(float) - vanilla_np[:, :, :, 1].astype(float), axis=2)
bad_spec_increase = np.mean(optimized_np[:, :, :, 2].astype(float) - optimized_np[:, :, :, 1].astype(float) - (vanilla_np[:, :, :, 2].astype(float) - vanilla_np[:, :, :, 1].astype(float)), axis=2)
cycle_reduce = np.mean(vanilla_np[:, :, :, 3].astype(float) - optimized_np[:, :, :, 3].astype(float), axis=2)
    
for j in range(num_traces):
    for k in range(num_batches):
        # print retire increase percent
        # skip when frontend is actually increased, or the benefit is negated
        x = opt_bars[1, j, k].get_x()
        y = opt_bars[1, j, k].get_height()
        if fe_reduce[j, k] > 0 and retire_increase[j, k] < fe_reduce[j, k]:
            axs[1, j].text(x, y, f'{(retire_increase[j, k] / fe_reduce[j, k]):.2%}')

        # print bad spec increase percent
        x = opt_bars[2, j, k].get_x()
        y = opt_bars[2, j, k].get_height()
        if fe_reduce[j, k] > 0 and bad_spec_increase[j, k] < fe_reduce[j, k]:
            axs[2, j].text(x, y, f'{(bad_spec_increase[j, k] / fe_reduce[j, k]):.2%}')

        # print cycle reduce percent
        # skip when cycles is actually increased
        x = opt_bars[3, j, k].get_x()
        y = opt_bars[3, j, k].get_height()
        if cycle_reduce[j, k] > 0:
            axs[3, j].text(x, y, f'{(cycle_reduce[j, k] * 4 / fe_reduce[j, k]):.2%}')

# print critical percentages
for i in range(num_series):
    # CPU clk cannot be naively calculated
    if printable_counters[i] == "cpu_clk_unhalted.thread_any:u":
        continue
    elif printable_counters[i] == "tsc_cycles":
        continue
    for j in range(num_traces):
        for k in range(num_batches):
            x = opt_bars[i, j, k].get_x()
            # y = opt_bars[i, j, k].get_height()
            diff_mean = np.mean(optimized_np[:, :, :, i].astype(float) - vanilla_np[:, :, :, i].astype(float), axis=2)
            vanilla_mean = np.mean(vanilla_np[:, :, :, i].astype(float), axis=2)
            axs[i, j].text(x, 0, f'{diff_mean[j, k] / vanilla_mean[j, k]:.2%}')

# print end to end results
for j in range(num_traces):
    for k in range(num_batches):
        try:
            perf_cycle_index = counters_printable.index("cpu_clk_unhalted.thread_any:u")
            x = opt_bars[perf_cycle_index, j, k].get_x()
            opt_cycles = np.mean(optimized_np[:, :, :, perf_cycle_index].astype(float), axis=2)
            van_cycles = np.mean(vanilla_np[:, :, :, perf_cycle_index].astype(float), axis=2)
            xput_percent = ((1e9/opt_cycles[j, k]) - (1e9/van_cycles[j, k])) / (1e9/van_cycles[j, k])
            axs[perf_cycle_index, j].text(x, 0, f'{xput_percent:.2%}')
        except:
            pass

        try:
            tsc_cycle_index = counters_printable.index("tsc_cycles")
            x = opt_bars[tsc_cycle_index, j, k].get_x()
            opt_cycles = np.mean(optimized_np[:, :, :, tsc_cycle_index].astype(float), axis=2)
            van_cycles = np.mean(vanilla_np[:, :, :, tsc_cycle_index].astype(float), axis=2)
            xput_percent = ((1e12/opt_cycles[j, k]) - (1e12/van_cycles[j, k])) / (1e12/van_cycles[j, k])
            axs[tsc_cycle_index, j].text(x, 0, f'{xput_percent:.2%}')
        except:
            pass

# print sub-events
optimized_unprint_np = np.array(optimized_unprintable)
vanilla_unprint_np = np.array(vanilla_unprintable)
# there are actually non-printable counters
if len(np.shape(optimized_unprint_np)) == 4:
    for j in range(num_traces):
        fe_all_opt_mean = np.mean(optimized_np[j, :, :, 0].astype(float), axis=1)
        fe_all_van_mean = np.mean(vanilla_np[j, :, :, 0].astype(float), axis=1)
        fe_latency_opt_mean = np.mean(optimized_unprint_np[j, :, :, 0].astype(float), axis=1)
        fe_latency_van_mean = np.mean(vanilla_unprint_np[j, :, :, 0].astype(float), axis=1)
        # print bw count
        # for k, b in enumerate(opt_bars[0, j, :]):
        #     axs[0, j].text(b.get_x(), b.get_height(), f'{((fe_all_opt_mean[k] - fe_latency_opt_mean[k] * 4) / (trace_reqs[j] if normalized == True else 1)):.3e}')
        
        # print bw reduce %
        for k, b in enumerate(opt_bars[0, j, :]):
            opt_bw = (fe_all_opt_mean[k] - fe_latency_opt_mean[k] * 4) / (trace_reqs[j] if normalized == True else 1)
            van_bw = (fe_all_van_mean[k] - fe_latency_van_mean[k] * 4) / (trace_reqs[j] if normalized == True else 1)
            axs[0, j].text(b.get_x(), b.get_height(), f'{(opt_bw - van_bw) / van_bw:.2%}')

        latency_bar_opt = axs[0, j].bar(x_axis-0.2, fe_latency_opt_mean * 4 / (trace_reqs[j] if normalized == True else 1), color='pink', width=0.4)
        latency_patch = matplotlib.patches.Patch(color='pink', label='fe-latency')
        bw_patch = matplotlib.patches.Patch(color='red', label='fe-bw')
        axs[0, j].legend(handles=[latency_patch, bw_patch])

        # print latency %
        # for k, b in enumerate(latency_bar_opt):
        #     axs[0, j].text(b.get_x(), b.get_height(), f'{fe_latency_opt_mean[k] * 4 / optimized_np[j, k, :, 0].astype(float).mean():.2%}')
        
        # print latency count
        # for k, b in enumerate(latency_bar_opt):
        #     axs[0, j].text(b.get_x(), b.get_height(), f'{fe_latency_opt_mean[k] * 4:.3e}')

        # print latency reduce %
        for k, b in enumerate(latency_bar_opt):
            axs[0, j].text(b.get_x(), b.get_height(), f'{(fe_latency_opt_mean[k] - fe_latency_van_mean[k])/fe_latency_van_mean[k]:.2%}')

        # latency_bar_van = axs[0, j].bar(x_axis+0.2, fe_latency_van_mean * 4 / (trace_reqs[j] if normalized == True else 1), color='cyan', width=0.4)
        # for k, b in enumerate(latency_bar_van):
        #     axs[0, j].text(b.get_x(), b.get_height(), f'{fe_latency_van_mean[k] * 4 / vanilla_np[j, k, :, 0].astype(float).mean():.2%}')

# FIXME
for c, ax in zip(printable_counters, axs):
    ax[0].set_ylabel(c)

for t, ax in zip(traces, axs[0]):
    ax.set_title(t)

# Show the plot
# plt.tight_layout()
# plt.show()

# assume the trace has name 'XXX_r%d_XXX.txt'
aligned = False
pinned = True if data_path.find('pinned') != -1 else False
L1_breakdown = True if data_path.find('L1') != -1 else False
enable_tsc = True if data_path.find('tsc') != -1 else False
sp_num = -1
for it in data_path.split('_'):
    if it.find('sp') != -1:
        sp_num = it.split('sp')[0]

if traces[0].find('align') != -1:
    aligned = True

m = re.search('r[0-9]+', data_path)
if m is not None:
    flow_cnt = m.group()[1:]
else:
    flow_cnt = 'mixed'

m = re.search('c1[a-zA-Z\-]+', data_path)
if m is not None:
    c1 = m.group()[2:]
else:
    c1 = 'opt'

m = re.search('c2[a-zA-Z\-]+', data_path)
if m is not None:
    c2 = m.group()[2:]
else:
    c2 = 'van'

plt.suptitle(f"Flow: {flow_cnt}, Aligned: {aligned}, Normalized: {normalized}, Pinned: {pinned}, L1: {L1_breakdown}, tsc: {enable_tsc}, component1: {c1}, component2: {c2}", size='xx-large')

fig_path = f'/home/iom/snort3-git/npl_util/{"align_" if aligned == True else ""}{"normalized_" if normalized == True else ""}{"pinned_" if pinned == True else ""}{f"{sp_num}sp_" if sp_num != -1 else ""}{"L1_" if L1_breakdown == True else ""}{"tsc_" if enable_tsc == True else ""}{c1}_{c2}_{flow_cnt}.png'
print(f"Writing to {fig_path}")
plt.savefig(fig_path)
