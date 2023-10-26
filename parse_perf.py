import tqdm
from typing import Tuple, List
import copy
# highlight high figures
from termcolor import colored

trace_name = "/home/iom/snort3-vanilla/logs/trace_insn-isolated-request.txt"

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
    # line pattern: snort <pid> <whatever> <time_second.time_nanosecond>: <address> <function_name_may_have_space>+<offset> <binary path> insn: <instruction_separated_by_space>
    split_line = [x.strip() for x in line.split()]
    # address is always #5
    addr = int(split_line[4], base=16)
    # function name is NOT always #6, but between <address> and <binary path>
    # function name should not contain '/'
    binary_idx = next((split_line.index(it) for it in split_line if '/' in it), None)
    try:
        func_name_list = split_line[5:binary_idx]
    except TypeError:
        print(binary_idx)
    # it will function normally if the list only has one element
    func_name = ' '.join(func_name_list)
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

def populate_in_inst_dict(addr : int, inst_dict: dict) -> bool:
    if addr not in inst_dict:
        inst_dict[addr] = 1
        return False
    else:
        return True

def return_from_function(insn : list, func_name : str, func_to_check : str) -> bool:
    if len(insn) != 1:
        return False
    if insn[0] != 'c3':
        return False
    # wildcard
    if func_to_check == '*':
        return True
    # exact match
    if func_name == func_to_check:
        return True
    # Under heavy optimization, some functions will be inlined to save the overhead of calls
    # In this case, find the last function that actually returns
    if func_name == 'snort::InspectorManager::probe' and func_to_check == 'snort::DetectionEngine::finish_inspect_with_latency':
        return True
    if func_name == 'snort::DetectionEngine::offload' and func_to_check == 'snort::DetectionEngine::detect':
        return True
    if func_name == 'TcpSession::restart' and func_to_check == 'snort::InspectorManager::bumble':
        return True 
    if func_name == 'Binder::handle_flow_service_change' and func_to_check == 'FlowServiceChangeHandler::handle':
        return True
    if func_name == 'AppIdSession::publish_appid_event' and func_to_check == 'AppIdDiscovery::do_post_discovery':
        return True
    # if len(insn) == 5 and insn[0] == 'e9' and insn[1] == '25' and insn[2] == '52' and insn[3] == '0b' and insn[4] == '00' and func_name == 'snort::DetectionEngine::finish_inspect_with_latency':
    #     return True
    # if len(insn) == 5 and insn[0] == 'e9' and insn[1] == '6e' and insn[2] == 'fd' and insn[3] == 'ff' and insn[4] == 'ff' and func_name == 'snort::DetectionEngine::detect':
    #     return True
    # if len(insn) == 2 and insn[0] == 'ff' and insn[1] == 'e0' and func_name == 'snort::InspectorManager::bumble':
    #     return True
    return False

def enter_function(func_name_raw : str, func_to_check : str) -> bool:
    if len(func_name_raw.split('+')) == 1:
        return False
    if func_name_raw.split('+')[1] == '0x0' and (func_name_raw.split('+')[0] == func_to_check or func_to_check == '*'):
        return True
    return False

def escape_function(func_name_raw : str, func_to_escape : list) -> bool:
    if len(func_name_raw.split('+')) == 1:
        return False
    for f in func_to_escape:
        if func_name_raw.split('+')[0].startswith(f):
            return True
    return False

def call_function(insn : list) -> bool:
    if len(insn) < 2:
        return False
    # `e8` is always `call`
    if insn[0] == 'e8':
        return True
    if insn[0] == 'ff':
        # only ff /2 and ff /3 is call
        second_byte = int(insn[1], base=16)
        reg = (second_byte >> 3) & 0b111
        if reg == 2 or reg == 3:
            return True
    # reg prefix
    if insn[0].startswith('4') == True:
        if len(insn) < 3:
            return False
        if insn[1] == 'ff':
            third_byte = int(insn[2], base=16)
            reg = (third_byte >> 3) & 0b111
            if reg == 2 or reg == 3:
                return True
    return False

def color_cache(num_cache : int, threshold : int=512) -> str:
    if num_cache >= threshold:
        return colored(str(num_cache), 'red')
    else:
        return str(num_cache)

def color_inst(num_inst : int, threshold : int=1500) -> str:
    if num_inst >= threshold:
        return colored(str(num_inst), 'red')
    else:
        return str(num_inst)

def function_breakdown(func_to_measure : str):
    num_lines = sum(1 for _ in open(trace_name, "r"))

    with open(trace_name, "r") as f:
        start = False
        call_stack = []
        call_sequence = []
        call_times = 0
        cache = {}
        inst_dict = {}
        curr_idx = 0
        is_call = False
        line_cumulate = 0
        inst_cumulate = 0
        for line in tqdm.tqdm(f, total=num_lines):
            addr, func_name_raw, insn = parse_line(line)
            # implicitly make calls to unrecognized functions to fall back to inner layers
            if len(func_name_raw.split('+')) == 1:
                continue
            func_name = func_name_raw.split('+')[0]
            func_off  = func_name_raw.split('+')[1]
            if enter_function(func_name_raw, func_to_measure) == True and start == False:
                start = True
                call_times += 1
                print("Breakdown of Function " + func_to_measure + "#" + str(call_times) + ":")
                call_stack.append((func_name_raw.split('+')[0], 0, 0))
                print("\t" * len(call_stack) + "CALL " + func_name)
            if start == False:
                continue
            
            # if func_off == '0x0' and escape_function(func_name_raw, ["malloc", "_int_free", "_int_malloc", "sysmalloc", "_", "["]) == False:
            #     seen = False
            #     for item in call_stack:
            #         if item[0] == func_name:
            #             seen = True
            #             curr_idx = call_stack.index(item)
            #     if seen == False:
            #         call_stack.append((func_name_raw.split('+')[0], 0, 0))
            #         curr_idx = -1
            
            if is_call == True:
                call_stack.append((func_name_raw.split('+')[0], 0, 0))
                print("\t" * len(call_stack) + "CALL " + func_name)
                curr_idx = -1
                is_call = False
                if len(call_stack) > 50:
                    # print(call_stack)
                    exit()

            cache_ret = populate_in_cache(addr, cache)
            inst_ret  = populate_in_inst_dict(addr, inst_dict)

            cache_ret = 1 if cache_ret == False else 0
            inst_ret = 1 if inst_ret == False else 0
            
            # cumulative results should go along with calling, not returning
            line_cumulate += cache_ret
            inst_cumulate += inst_ret
            if line_cumulate >= 512:
                line_cumulate = 0
                print("=== reaching cache capacity ===")
            if inst_cumulate >= 1500:
                inst_cumulate = 0
                print("=== reaching instrucion capacity ===")

            try:
                call_stack[curr_idx] = (call_stack[curr_idx][0], call_stack[curr_idx][1] + cache_ret, call_stack[curr_idx][2] + inst_ret)
            except IndexError:
                print("Finding indexing error on call_stack!")
                print(f"Curr index: {curr_idx}, Call_stack: {call_stack}")
                exit()

            if call_function(insn) == True:
                is_call = True

            # this will cause malloc unable to return
            # if return_from_function(insn, func_name, '*') and escape_function(func_name_raw, ["malloc", "_int_free", "_int_malloc", "sysmalloc", "_"]) == False:
            if return_from_function(insn, func_name, '*') == True:
                stack_depth = len(call_stack)
                # the structure of call_sequence: (call_stack_object, current_depth)
                print("\t" * stack_depth + "RETURN " + f"{func_name}, lines: {call_stack[-1][1]}, insts: {call_stack[-1][2]}")
                call_sequence.append((call_stack.pop(), stack_depth))
                # if the function we are interested in returns, the call stack must be empty
                if return_from_function(insn, func_name, func_to_measure) == True:
                    assert(len(call_stack) == 0)
                if len(call_stack) != 0:
                    # print("returning from a function, depth:" + str(len(call_stack)))
                    continue
                print(f"Call_sequence: {call_sequence}")
                # print("Breakdown of Function " + func_to_measure + "#" + str(call_times) + ":")
                line_sum = 0
                inst_sum = 0
                for f in call_sequence:
                    line_sum += f[0][1]
                    inst_sum += f[0][2]
                print(f"Total: {line_sum} lines, {inst_sum} instructions")
                
                for f in call_sequence:
                    # if there is no new line and no new instructions, it is a call to old functions
                    if f[0][1] == 0 and f[0][2] == 0:
                        continue
                    # hide small results, though they may build up
                    # if f[0][1] < line_sum * 0.05 or f[0][2] < inst_sum * 0.05:
                    #     continue
                    # print("\t" * f[1] + "RETURN " + f"{f[0][0]}: lines: {color_cache(f[0][1])}, insts: {color_inst(f[0][2])}")
                call_stack.clear()
                call_sequence.clear()
                cache.clear()
                inst_dict.clear()
                start = False
                line_cumulate = 0
                inst_cumulate = 0

def measure_function(func_to_measure : str, sub_func_to_measure : list = []):
    num_lines = sum(1 for _ in open(trace_name, "r"))
    cache = {}
    breakdown = {}
    # serving recursive calls
    recur_stack = []
    # deepest layer
    deepest_call = 0
    # monitoring instruction count
    inst_dict = {}
    inst_breakdown = {}

    with open(trace_name, "r") as f:
        start = False
        curr_num = 0
        curr_idx = -1
        curr_line = 0
        for line in tqdm.tqdm(f, total=num_lines):
        # for line in f: 
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
            # if ignore_function(func_name, ["malloc", "_int_free", "_int_malloc", "sysmalloc"]):
            #     continue
            ret = populate_in_cache(addr, cache)
            insn_ret = populate_in_inst_dict(addr, inst_dict)
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
                if insn_ret == False and curr_idx >= 0:
                    try:
                        inst_breakdown[sub_func_to_measure[curr_idx]] += 1
                    except KeyError:
                        inst_breakdown[sub_func_to_measure[curr_idx]] = 1
                # reset
                # if func_name == sub_func_to_measure[curr_idx] and return_from_function(insn):
                if return_from_function(insn, func_name, sub_func_to_measure[curr_idx]):
                    curr_idx = -1
            
            # no matter how the breakdown is, do a hard reset
            # if func_name == func_to_measure and return_from_function(insn):
            if return_from_function(insn, func_name, func_to_measure):
                # only print if we have no sub functions to trace
                print("Number of cachelines of function " + func_to_measure + "#" + str(curr_num) + ": ", end="") 
                print(colored(str(len(cache)), 'red') if len(cache) > 512 else str(len(cache)))
                if len(sub_func_to_measure) != 0:
                    total = 0
                    for fn in sub_func_to_measure:
                        # some function we are interested in might not present
                        try:
                            print(f"\t{fn}:", end="")
                            print(colored(str(breakdown[fn]), 'red') if breakdown[fn] > 512 else str(breakdown[fn]), end="")
                            print(f"({float(breakdown[fn]) / len(cache):.1%})", end="")
                            total += float(breakdown[fn]) / len(cache)
                            # print instruction count, highlight when it's exceeding DSB
                            print("(", end="")
                            print(colored(str(inst_breakdown[fn]), 'red') if inst_breakdown[fn] > 1500 else str(inst_breakdown[fn]), end="")
                            print(")", end="")
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
                    inst_dict.clear()
                    inst_breakdown.clear()
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
# measure_function("snort::InspectorManager::internal_execute<false>", ["StreamBase::eval", "Normalizer::eval", "TcpSession::process", "AppIdInspector::eval", "HttpInspect::eval", "snort::InspectorManager::bumble"])
# measure_function("TcpSession::process", ["TcpStateMachine::eval", "TcpSession::check_events_and_actions", "S5TraceTCP"])
# measure_function("TcpStateMachine::eval", ["TcpStreamTracker::set_tcp_event", "TcpSession::validate_packet_established_session", "TcpStateCloseWait::data_seg_sent", "TcpStateFinWait1::ack_recv" ])
# measure_function("TcpStateMachine::eval", ["TcpReassembler::flush_on_ack_policy"])
# measure_function("TcpStateCloseWait::data_seg_sent", ["TcpReassembler::flush_on_ack_policy"])
# measure_function("TcpStateMachine::eval", ["TcpReassembler::scan_data_post_ack", "TcpReassembler::flush_to_seq", "TcpReassembler::purge_to_seq"])
# measure_function("TcpStateMachine::eval", ["TcpReassembler::flush_data_segments", "Analyzer::inspect_rebuilt"])
# measure_function("process_packet", ["StreamBase::eval", "Normalizer::eval", "TcpSession::process", "AppIdInspector::eval", "HttpInspect::eval", "snort::InspectorManager::bumble"])
# measure_function("process_packet", ["TcpReassembler::scan_data_post_ack", "TcpReassembler::initialize_pdu", "TcpReassembler::flush_data_segments", "HttpInspect::eval"])
# measure_function("Analyzer::inspect_rebuilt", ["HttpInspect::eval"])
# measure_function("process_packet", ["Analyzer::inspect_rebuilt"])
# measure_function("process_packet", ["AppIdDiscovery::do_pre_discovery", "AppIdDiscovery::do_discovery", "AppIdDiscovery::do_post_discovery"])
# measure_function("StreamBase::eval", ["FlowCache::allocate", "snort::Flow::init", "snort::DataBus::publish"])

# function_breakdown("StreamBase::eval")
function_breakdown("AppIdInspector::eval")

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
