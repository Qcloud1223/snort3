import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import sys
import re
import functools

if len(sys.argv) < 2:
    print("usage: python plot_expr_new.py trace_name1 trace_name2 ... <normalized>")
    exit(-1)
else:
    data_paths = sys.argv[1:-1]
normalized = True if sys.argv[-1] == '1' else False

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

printable_counters_alias = [
    "fronend stall",
    "",
    "",
    "end to end (perf)",
    "",
    "",
    "",
    "",
    "",
    "",
    "end to end (tsc)",
    "iTLB stall",
    "icache stall #1",
    "icache stall #2",
    "resteer stall",
    "",
    "",
    "",
    ""
]

unprintable_counters = [
    "idq_uops_not_delivered.cycles_0_uops_deliv.core:u"
]

color_pool = [
    '#fbe5d6',
    '#fff2cc',
    '#deebf7',
    '#e2f0d9',
    '#f8cbad',
    '#ffe699',
    '#bdd7ee',
    "#c5e0b4"
]

def label_to_value(i):
    if i == "van":
        return 0
    elif i == "van-huge":
        return 1
    elif i == "opt":
        return 2
    elif i == "opt-huge":
        return 3
    else:
        return 999

def bar_layout(item1, item2):
    return label_to_value(item1[0]) - label_to_value(item2[0])

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
printable_data = []
unprintable_data = []
traces = []
batches = []
printable_ctr = []
unprintable_ctr = []
components = []
for data_path in data_paths:
    with open(data_path) as f:
        optimized_printable, optimized_unprintable, vanilla_printable, vanilla_unprintable, trace, batch, counters_printable, counters_unprintable = parse_data(f)
        printable_data.append(np.array(optimized_printable))
        printable_data.append(np.array(vanilla_printable))
        unprintable_data.append(np.array(optimized_unprintable))
        unprintable_data.append(np.array(vanilla_unprintable))
        # they are the same, so do it twice
        traces.append(np.array(trace))
        traces.append(np.array(trace))
        batches.append(np.array(batch))
        batches.append(np.array(batch))
        printable_ctr.append(np.array(counters_printable))
        printable_ctr.append(np.array(counters_printable))
        unprintable_ctr.append(np.array(counters_unprintable))
        unprintable_ctr.append(np.array(counters_unprintable))
    
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
    components.append(c1)
    components.append(c2)

# sort them according to name
components, printable_data, unprintable_data, traces, batches, printable_ctr, unprintable_ctr = map(
    list, zip(*sorted(zip(components, printable_data, unprintable_data, traces, batches, printable_ctr, unprintable_ctr), key=functools.cmp_to_key(bar_layout)))
)

num_series = printable_ctr[0].size
num_batches = batches[0].size
num_traces = traces[0].size
num_repeats = printable_data[0].shape[3]
# how many bars are we drawing, to later draw bars according to arange
num_bars = len(printable_data)
# we get around 0.8 width per iteration
bar_width = 0.8 / num_bars

print(f"num_series: {num_series}, num_batches: {num_batches}, num_traces: {num_traces}, num_repeats: {num_repeats}, num_bars: {num_bars}")

# get the request number of each trace
trace_reqs = []
if normalized == True:
    # it makes no sense if each data series is not under the same trace
    for t in traces[0]:
        m = re.search('f[0-9]+', t)
        if m is not None:
            request_cnt = int(m.group()[1:])
        else:
            print(f"Normalizing trace name: {t}, but it does not conform to format?")
            exit(-1)
        trace_reqs.append(request_cnt)

# Prepare the figure and axis
fig, axs = plt.subplots(num_series, num_traces, figsize=(24, num_series * 2))

# convert the ax into 2d array for later indicing
# note that subplots will not return array of axes if the dimension is 1
# FIXME
if num_traces == 1:
    axs = np.atleast_2d(axs)
    axs = np.transpose(axs)

x_axis = np.arange(batches[0].size)
# batches = np.array(batches)
all_bars = np.ndarray(shape=(num_series, num_traces, num_batches, num_bars), dtype=matplotlib.patches.Rectangle)
# van_bars = np.array((num_series, num_traces, num_batches))

for i in range(num_series):
    ymax = 0
    for j in range(num_traces):
        # batch_data = np.zeros(num_batches)
        mean = np.zeros(num_batches)
        std = np.zeros(num_batches)
        yerr = np.zeros((2, 1))

        for k in range(num_batches):
            # print(f"i: {i}, j: {j}, k:{k}")
            # print each bar
            for x in range(num_bars):
                data = printable_data[x][j, k, :, i].astype(float)
                mean = data.mean()
                std = data.std()
                yerr[0, 0] = (mean - min(data)) / (trace_reqs[j] if normalized == True else 1)
                yerr[1, 0] = (max(data) - mean) / (trace_reqs[j] if normalized == True else 1)
                all_bars[i, j, k, x], = axs[i, j].bar(x_axis[k] - 0.4 + bar_width * x, mean / (trace_reqs[j] if normalized == True else 1), color=color_pool[x], width=bar_width, yerr=yerr)
                ymax = max(ymax, max(data) / (trace_reqs[j] if normalized == True else 1))      
        axs[i, j].set_xticks(x_axis, batches[0])
        
    if normalized == True:
        for j in range(num_traces):
            axs[i, j].set_ylim(0, ymax*1.1)
            # axs[i, j].set_title(f'Trace: {j}, counter: {i}')
            # axs[i, j].set_xlabel('batch size')
            # axs[i, j].set_ylabel('counts')

# print convert percentage
for j in range(num_traces):
    for k in range(num_batches):
        for x in range(1, num_bars):
            # print retire increase percent
            # skip when frontend is actually increased, or the benefit is negated
            x_pos = all_bars[1, j, k, x].get_x()
            y = all_bars[1, j, k, x].get_height()
            fe_reduce = np.mean(printable_data[0][:, :, :, 0].astype(float) - printable_data[x][:, :, :, 0].astype(float), axis=2)
            retire_increase = np.mean(printable_data[x][:, :, :, 1].astype(float) - printable_data[0][:, :, :, 1].astype(float), axis=2)
            bad_spec_increase = np.mean(printable_data[x][:, :, :, 2].astype(float) - printable_data[x][:, :, :, 1].astype(float) - printable_data[0][:, :, :, 2].astype(float) + printable_data[0][:, :, :, 1].astype(float), axis=2)
            cycle_reduce = np.mean(printable_data[0][:, :, :, 3].astype(float) - printable_data[x][:, :, :, 3].astype(float), axis=2)
            
            if fe_reduce[j, k] > 0 and retire_increase[j, k] < fe_reduce[j, k]:
                axs[1, j].text(x_pos, y, f'{(retire_increase[j, k] / fe_reduce[j, k]):.2%}')

            # print bad spec increase percent
            x_pos = all_bars[2, j, k, x].get_x()
            y = all_bars[2, j, k, x].get_height()
            if fe_reduce[j, k] > 0 and bad_spec_increase[j, k] < fe_reduce[j, k]:
                axs[2, j].text(x_pos, y, f'{(bad_spec_increase[j, k] / fe_reduce[j, k]):.2%}')

            # print cycle reduce percent
            # skip when cycles is actually increased
            x_pos = all_bars[3, j, k, x].get_x()
            y = all_bars[3, j, k, x].get_height()
            if cycle_reduce[j, k] > 0:
                axs[3, j].text(x_pos, y, f'{(cycle_reduce[j, k] * 4 / fe_reduce[j, k]):.2%}')

# print critical percentages
for i in range(num_series):
    # CPU clk cannot be naively calculated
    if printable_counters[i] == "cpu_clk_unhalted.thread_any:u":
        continue
    elif printable_counters[i] == "tsc_cycles":
        continue
    for j in range(num_traces):
        for k in range(num_batches):
                for x in range(1, num_bars):
                    # calculate % compared with the first bar
                    x_pos = all_bars[i, j, k, x].get_x()
                    diff_mean = np.mean(printable_data[x][:, :, :, i].astype(float) - printable_data[0][:, :, :, i].astype(float), axis=2)
                    vanilla_mean = np.mean(printable_data[0][:, :, :, i].astype(float), axis=2)
                    axs[i, j].text(x_pos, 0, f'{diff_mean[j, k] / vanilla_mean[j, k]:.2%}', fontsize=9)

# print end to end results
for j in range(num_traces):
    for k in range(num_batches):
        for x in range(1, num_bars):
            try:
                perf_cycle_index = list(printable_ctr[0]).index("cpu_clk_unhalted.thread_any:u")
                x_pos = all_bars[perf_cycle_index, j, k, x].get_x()
                opt_cycles = np.mean(printable_data[x][:, :, :, perf_cycle_index].astype(float), axis=2)
                van_cycles = np.mean(printable_data[0][:, :, :, perf_cycle_index].astype(float), axis=2)
                xput_percent = ((1e9/opt_cycles[j, k]) - (1e9/van_cycles[j, k])) / (1e9/van_cycles[j, k])
                axs[perf_cycle_index, j].text(x_pos, 0, f'{xput_percent:.2%}')
            except:
                pass

            try:
                tsc_cycle_index = list(printable_ctr[0]).index("tsc_cycles")
                x_pos = all_bars[tsc_cycle_index, j, k, x].get_x()
                opt_cycles = np.mean(printable_data[x][:, :, :, tsc_cycle_index].astype(float), axis=2)
                van_cycles = np.mean(printable_data[0][:, :, :, tsc_cycle_index].astype(float), axis=2)
                xput_percent = ((1e9/opt_cycles[j, k]) - (1e9/van_cycles[j, k])) / (1e9/van_cycles[j, k])
                axs[tsc_cycle_index, j].text(x_pos, 0, f'{xput_percent:.2%}')
            except:
                pass

# print sub-events

# there are actually non-printable counters
if len(unprintable_ctr[0]) != 0:
    for j in range(num_traces):
        for k in range(num_batches):
            for x in range(num_bars):
                fe_all_mean = np.mean(printable_data[x][j, k, :, 0].astype(float))
                fe_latency_mean = np.mean(unprintable_data[x][j, k, :, 0].astype(float))
                fe_all_mean_van = np.mean(printable_data[0][j, k, :, 0].astype(float))
                fe_latency_mean_van = np.mean(unprintable_data[0][j, k, :, 0].astype(float))
                # print bw count
                # for k, b in enumerate(opt_bars[0, j, :]):
                #     axs[0, j].text(b.get_x(), b.get_height(), f'{((fe_all_opt_mean[k] - fe_latency_opt_mean[k] * 4) / (trace_reqs[j] if normalized == True else 1)):.3e}')
        
                # print bw reduce %
                opt_bw = (fe_all_mean - fe_latency_mean * 4) / (trace_reqs[j] if normalized == True else 1)
                van_bw = (fe_all_mean_van - fe_latency_mean_van * 4) / (trace_reqs[j] if normalized == True else 1)
                if x != 0:
                    b = all_bars[0, j, k, x]
                    axs[0, j].text(b.get_x(), b.get_height(), f'{(opt_bw - van_bw) / van_bw:.2%}')

                latency_bar_opt = axs[0, j].bar(x_axis[k] - 0.4 + bar_width * x, fe_latency_mean * 4 / (trace_reqs[j] if normalized == True else 1), color=color_pool[x+num_bars], width=bar_width)
                axs[0, j].text(latency_bar_opt[0].get_x(), latency_bar_opt[0].get_height(), f'{(fe_latency_mean - fe_latency_mean_van)/fe_latency_mean_van:.2%}')
            
        handles = []
        for x in range(num_bars):
            # handles.append(matplotlib.patches.Patch(color=color_pool[x], label='fe-bw'))
            handles.append(matplotlib.patches.Patch(color=color_pool[x+num_bars], label='fe-latency'))    
        axs[0, j].legend(handles=handles)

# FIXME
for c, ax in zip(printable_counters, axs):
    idx = printable_counters.index(c)
    ax[0].set_ylabel(c if printable_counters_alias[idx] == "" else printable_counters_alias[idx])

for t, ax in zip(traces, axs[0]):
    ax.set_title(t)

# Show the plot
# plt.tight_layout()
# plt.show()

# assume the trace has name 'XXX_r%d_XXX.txt'
aligned = False
pinned = True if data_paths[0].find('pinned') != -1 else False
L1_breakdown = True if data_paths[0].find('L1') != -1 else False
enable_tsc = True if data_paths[0].find('tsc') != -1 else False
sp_num = -1
for it in data_path[0].split('_'):
    if it.find('sp') != -1:
        sp_num = it.split('sp')[0]

if traces[0][0].find('align') != -1:
    aligned = True

m = re.search('r[0-9]+', data_paths[0])
if m is not None:
    flow_cnt = m.group()[1:]
else:
    flow_cnt = 'mixed'

handles = []
components_suffix = ""
for x in range(num_bars):
    patch = matplotlib.patches.Patch(color=color_pool[x], label=components[x])
    handles.append(patch)
    components_suffix += f"{components[x]}_"
fig.legend(handles=handles, fontsize="20")

plt.suptitle(f"Flow: {flow_cnt}, Aligned: {aligned}, Normalized: {normalized}, Pinned: {pinned}, L1: {L1_breakdown}, tsc: {enable_tsc}, components: {components}", size='xx-large')

fig_path = f'/home/iom/snort3-git/npl_util/{"align_" if aligned == True else ""}{"normalized_" if normalized == True else ""}{"pinned_" if pinned == True else ""}{f"{sp_num}sp_" if sp_num != -1 else ""}{"L1_" if L1_breakdown == True else ""}{"tsc_" if enable_tsc == True else ""}{components_suffix}{flow_cnt}.png'
print(f"Writing to {fig_path}")
plt.savefig(fig_path)
