import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

data_path = "/home/iom/snort3-vanilla/http_request_only.txt"
normalized = False

counters = [
    "idq_uops_not_delivered.core:u",
    "uops_retired.retire_slots:u",
    "uops_issued.any:u",
    "cpu_clk_unhalted.thread_any:u",
    "L1-icache-misses",
    "L1-dcache-misses",
    "LLC-load",
    "LLC-load-misses",
    "LLC-store",
    "LLC-store-misses"
]

def parse_data(f):
    # lines = f.readlines().strip().split('\n')
    batches = []
    traces = []
    counters = []
    # all_batch_data = []
    # all_trace_data = []
    optimized_data = []
    vanilla_data = []
    current_data = []
    
    for line in f.readlines():
        line = line.strip()
        if line.startswith("batch size:"):
            batches.append(int(line.split(":")[1].strip()))
            # all_trace_data[-1].append([])
            optimized_data[-1].append([])
            vanilla_data[-1].append([])
        elif line.startswith("trace:"):
            traces.append(line.split(":")[1].strip().split('/')[-1])
            # all_trace_data.append([])
            optimized_data.append([])
            vanilla_data.append([])
        elif line in ["Optimized:", "Vanilla:"]:
            if line.startswith("Optimized"):
                data_to_write = optimized_data
            else:
                data_to_write = vanilla_data
        # line break note us to push current sample 
        elif not line:
            if len(current_data) != 0:
                data_to_write[-1][-1].append(tuple(current_data))
                current_data = []
        elif line.startswith('-'):
            batches = []
        elif line.startswith('//'):
            continue
        else:
            current_data.append(int(line.split()[0].replace(',', '')))
    
    return optimized_data, vanilla_data, traces, batches 

# Parse the provided data
with open(data_path) as f:
    optimized_data, vanilla_data, traces, batches = parse_data(f)

# print(optimized_data)

num_series = len(optimized_data[0][0][0])
num_batches = len(batches)
num_traces = len(traces)
num_repeats = len(optimized_data[0][0])

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

optimized_np = np.array(optimized_data)
vanilla_np = np.array(vanilla_data)

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
        axs[i, j].set_ylim(0, ymax*1.1)
        # axs[i, j].set_title(f'Trace: {j}, counter: {i}')
        # axs[i, j].set_xlabel('batch size')
        # axs[i, j].set_ylabel('counts')

# print convert percentage
fe_reduce = np.mean(vanilla_np[:, :, :, 0].astype(float) - optimized_np[:, :, :, 0].astype(float), axis=2)
retire_increase = np.mean(optimized_np[:, :, :, 1].astype(float) - vanilla_np[:, :, :, 1].astype(float), axis=2)
bad_spec_increase = np.mean(optimized_np[:, :, :, 2].astype(float) - optimized_np[:, :, :, 1].astype(float) - (vanilla_np[:, :, :, 2].astype(float) - vanilla_np[:, :, :, 1].astype(float)), axis=2)
cycle_reduce = np.mean(vanilla_np[:, :, :, 3].astype(float) - optimized_np[:, :, :, 3].astype(float), axis=2)

# print(fe_reduce)
    
for j in range(num_traces):
    for k in range(num_batches):
        # print retire increase percent
        x = opt_bars[1, j, k].get_x()
        y = opt_bars[1, j, k].get_height()
        axs[1, j].text(x, y, f'{(retire_increase[0, k] / fe_reduce[0, k]):.2%}')

        # print bad spec increase percent
        x = opt_bars[2, j, k].get_x()
        y = opt_bars[2, j, k].get_height()
        axs[2, j].text(x, y, f'{(bad_spec_increase[0, k] / fe_reduce[0, k]):.2%}')

        # print cycle reduce percent
        x = opt_bars[3, j, k].get_x()
        y = opt_bars[3, j, k].get_height()
        axs[3, j].text(x, y, f'{(cycle_reduce[0, k] * 4 / fe_reduce[0, k]):.2%}')

for c, ax in zip(counters, axs):
    ax[0].set_ylabel(c)

for t, ax in zip(traces, axs[0]):
    ax.set_title(t)

# Show the plot
# plt.tight_layout()
# plt.show()

# assume the trace has name 'XXX_r%d_XXX.txt'
aligned = False
pinned = True if data_path.find('pinned') != -1 else False
if traces[0].find('align') != -1:
    aligned = True
try:
    flow_cnt = data_path.split('r')[-1].split('.')[0].split('_')[0]
    flow_cnt = int(flow_cnt)
except ValueError:
    print(f"Cannot parse string {flow_cnt}")
    flow_cnt = 'mixed'
plt.suptitle(f"Flow: {flow_cnt}, Aligned: {aligned}, Normalized: {normalized}, Pinned: {pinned}", size='xx-large')


fig_path = f'/home/iom/snort3-git/npl_util/{"align_" if aligned == True else ""}{"normalized_" if normalized == True else ""}{"pinned_" if pinned == True else ""}{flow_cnt}.png'
print(f"Writing to {fig_path}")
plt.savefig(fig_path)
