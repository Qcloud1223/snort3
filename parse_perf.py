import tqdm
from typing import Tuple, List
import copy

trace_name = "trace_insn-3f2.txt"

def ignore_function(func : str, ignore: list) -> bool:
    # ignore_list = [
    #     # all function that starts with dl
    #     "_dl_",
    #     # dynamic linker internal function that surprisingly does not starts with _
    #     "do_lookup_x"
    # ]
    for name in ignore:
        if func.startswith(name) == True:
            return True
    
    return False

def parse_line(line : str) -> Tuple[int, str, List[str]]:
    split_line = [x.strip() for x in line.split()]
    # address is always #5
    addr = int(split_line[4], base=16)
    # function name is always #6
    func_name = split_line[5]
    # 'insn'
    idx = split_line.index('insn:')
    insn = [x for x in split_line[idx+1:]]
    return addr, func_name, insn

def populate_in_cache(addr : int, cache : dict) -> bool:
    try:
        _ = cache[addr >> 6]
    except KeyError:
        cache[addr >> 6] = 1
        return False
    else:
        return True

def return_from_function(insn : list, func_name : str, func_to_check : str) -> bool:
    if func_name != func_to_check:
        return False
    # explicit return
    if len(insn) == 1 and insn[0] == 'c3':
        return True
    # some functions does not explicitly return
    # In this case, use their name in accord with finializing instructions
    if len(insn) == 5 and insn[0] == 'e9' and insn[1] == '25' and insn[2] == '52' and insn[3] == '0b' and insn[4] == '00':
        return True
    if len(insn) == 5 and insn[0] == 'e9' and insn[1] == '6e' and insn[2] == 'fd' and insn[3] == 'ff' and insn[4] == 'ff':
        return True
    if len(insn) == 2 and insn[0] == 'ff' and insn[1] == 'e0' and func_name == 'snort::InspectorManager::bumble':
        return True
    return False

def enter_function(func_name_raw : str, func_to_check : str) -> bool:
    if len(func_name_raw.split('+')) == 1:
        return False
    if func_name_raw.split('+')[1] == '0x0' and func_name_raw.split('+')[0] == func_to_check:
        return True
    return False

def measure_function(func_to_measure : str, sub_func_to_measure : list = []):
    num_lines = sum(1 for _ in open(trace_name, "r"))
    cache = {}
    breakdown = {}
    # serving recursive calls
    recur_stack = []
    # deepest layer
    deepest_call = 0

    with open(trace_name, "r") as f:
        start = False
        curr_num = 0
        curr_idx = -1
        curr_line = 0
        for line in tqdm.tqdm(f, total=num_lines):
            curr_line += 1
            addr, func_name_raw, insn = parse_line(line)
            func_name = func_name_raw.split('+')[0]

            if enter_function(func_name_raw, func_to_measure):
                if start == True:
                    # recursive call, saving context
                    recur_stack.append(tuple([copy.deepcopy(cache), copy.deepcopy(breakdown), curr_num]))
                    deepest_call += 1
                    curr_num = deepest_call
                # print("start function #" + str(curr_num) + " at line #" + str(curr_line) + ", Recursive: " + str(start))
                start = True
            if start == False:
                continue
            # we've found the first occurence. Now, we might want a breakdown of inner functions
            # ignore malloc and its family
            if ignore_function(func_name, ["malloc", "_int_free", "_int_malloc", "sysmalloc"]):
                continue
            ret = populate_in_cache(addr, cache)
            # this cacheline is caused by function we are interested in,
            # start tracing one of the functions
            # WARNING: the user is responsible to check those functions does not overlap
            if len(sub_func_to_measure) != 0:
                if (func_name in sub_func_to_measure) and curr_idx == -1:
                    curr_idx = sub_func_to_measure.index(func_name)
                    # print("find function: " + func_name + ", setting index to " + str(curr_idx))
                # record breakdown on for active functions 
                if ret == False and curr_idx >= 0:
                    try:
                        # must fetch function name to trace since func_name can contain inner functions
                        breakdown[sub_func_to_measure[curr_idx]] += 1
                    except KeyError:
                        breakdown[sub_func_to_measure[curr_idx]] = 1
                # reset
                # if func_name == sub_func_to_measure[curr_idx] and return_from_function(insn):
                if return_from_function(insn, func_name, sub_func_to_measure[curr_idx]):
                    curr_idx = -1
            
            # no matter how the breakdown is, do a hard reset
            # if func_name == func_to_measure and return_from_function(insn):
            if return_from_function(insn, func_name, func_to_measure):
                # only print if we have no sub functions to trace
                print("Number of cachelines of function " + func_to_measure + "#" + str(curr_num) + ": " + str(len(cache)) )
                if len(sub_func_to_measure) != 0:
                    total = 0
                    for fn in sub_func_to_measure:
                        # some function we are interested in might not present
                        try:
                            print(f"\t{fn}: {breakdown[fn]} ({float(breakdown[fn]) / len(cache):.1%})", end="")
                            total += float(breakdown[fn]) / len(cache)
                        except KeyError:
                            pass
                    print(f"\t-> coverage: {total:.1%}")
                # print("end function #" + str(curr_num) + " at line #" + str(curr_line))
                # a layer has been returned, check the stack: if there is something, resume
                if len(recur_stack) != 0:
                    cache, breakdown, curr_num = recur_stack.pop()
                else:
                    # if we finally reach here, we need to resume from the deepest
                    deepest_call += 1
                    curr_num = deepest_call
                    start = False
                    # TODO: we might be interested in the union of all packets
                    cache.clear()
                    breakdown.clear()
                # return

# measure_function("StreamBase::eval")
# measure_function("TcpSession::process")
# measure_function("AppIdInspector::eval")
# measure_function("PortScan::eval")
# measure_function("snort::InspectorManager::internal_execute<false>")
# measure_function("snort::InspectorManager::probe")
# measure_function("process_packet")

# top level breakdown: internal execute has at least 50% of the instructions
# measure_function("process_packet", ["snort::InspectorManager::internal_execute<false>", "snort::DetectionEngine::detect", "snort::DetectionEngine::finish_inspect_with_latency", "snort::DetectionEngine::finish_inspect"])
# internal_execute breakdown: one packet does not call this function exactly once
measure_function("snort::InspectorManager::internal_execute<false>", ["StreamBase::eval", "Normalizer::eval", "TcpSession::process", "AppIdInspector::eval", "HttpInspect::eval", "snort::InspectorManager::bumble"])

# num_lines = sum(1 for _ in open(trace_name, "r"))

# with open(trace_name, "r") as f:
#     all_cache_line = {}
#     all_instruction = {}
#     for line in tqdm.tqdm(f, total=num_lines):
#         addr, func_name, _ = parse_line(line)
#         if ignore_function(func_name, ["_dl_", "do_lookup_x"]) == True:
#             continue
#         addr_cache = (addr >> 6) << 6
#         all_cache_line[addr_cache] = 1
#         all_instruction[addr] = 1
    
#     print("Number of instructions:", len(all_instruction))
#     print("Number of cachelines:", len(all_cache_line))
