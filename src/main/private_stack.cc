/* enable assertion in this TU only */
// #undef NDEBUG
/* enable logs even if optimization is enabled */
// #define DEBUG_MSGS
// #undef DEBUG_MSGS
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include "private_stack.h"
/* import top-level build options generated by cmake
 * Note: snort ignore all asserts when `--enable-debug` is disabled,
 * which is necessary for us -- a single check in context->start()
 * will fail, and there might be hundreds of similar checks ahead
 * However, snort is configured to only disable `NDEBUG` with this option,
 * so I have no choice but to move to `DEBUG_MSGS`,
 * which seems to only enable mere debug logs (Phew!)
 */
#include "config.h"

#define likely(x)       __builtin_expect(!!(x), 1)
#define unlikely(x)     __builtin_expect(!!(x), 0)

RegSet DefaultStack;
void *StackTops[MAX_STACK_NUM];
RegSet RestoreRegs[MAX_STACK_NUM];
int CurrStack = 0;
unsigned ReservedStacks = 0;
static unsigned flowIdxCtr = 0;
static int redoIdx = 0;
#ifdef DEBUG_MSGS
static uint64_t processedPkts = 0;
#endif

// static int finished_idx = -1;
/* NB: all operation against this vector should be 64 bit */
// static uint64_t finished_vector;
// static bool all_stacks_initialized = false;
// static uint64_t locked_vector;
static uint64_t available_vector;

// static std::set<uint64_t> seenFlow;
/* key: flow *, value: packet vector */
// static std::unordered_map<uint64_t, uint64_t> seenFlow;
static uint64_t seenFlow[MAX_STACK_NUM];
static unsigned seenFlowSize;
static std::vector<int> redoQueue;
// void *redoAddr;
/* depending on the last pkt has flow or not, this is set upon two conditions:
 * 1. the last packet ends
 * 2. the last packet finds its flow
 */
bool all_flows_initialized;

void init_stacks()
{
    size_t wholesize = MAX_STACK_NUM * MAX_STACK_SIZE;
    /* according to ABI, stack must be aligned to 16 bytes */
    void *allstacks = aligned_alloc(16, wholesize);
    /* since stack grow downwards, assign values to them reversely, too */
    for (int i = MAX_STACK_NUM - 1; i >= 0; i--) {
        allstacks = (void *)((size_t)allstacks + MAX_STACK_SIZE);
        StackTops[i] = allstacks;
    }
}

void reserve_stacks(unsigned num)
{
#ifdef DEBUG_MSGS
    fprintf(stderr, "[Rev] Reserving %u stacks\n", num);
#endif
    assert(num <= MAX_STACK_NUM);
    /* packets from the last batch must all be freed */
    // assert(available_vector == 0 || flowIdxCtr == 0);
    NumStacks = num;
    ReservedStacks = 0;
    flowIdxCtr = 0;
    available_vector = UINT64_MAX;
    all_flows_initialized = false;
    // seenFlow.clear();
    /* redo queue must be flushed, otherwise, it's taking up buffer */
    assert(redoQueue.empty());
    redoIdx = 0;
    /* TODO: don't manually set this, shrink flow table instead */
    seenFlowSize = 0;
}

/* NB: stack index can be negative! */
void stack_switch(int from, int to)
{
    RegSet *fromStack = from < 0 ? &DefaultStack : &CalleeRegs[from];
    RegSet *toStack   = to < 0 ? &DefaultStack : &CalleeRegs[to];
    /* manually set stack index (instead of self-inc) when switching */
    CurrStack = to;
    StackSwitchAsm(fromStack, toStack);
}

static inline int get_key_from_flow_ptr(uint64_t flow)
{
    int *flowInt = reinterpret_cast<int *>(flow);
    /* magic number retrieved from disassembly */
    return *(flowInt + 94);
}

static inline void set_key_to_flow_ptr(uint64_t flow, int idx)
{
    int *flowInt = reinterpret_cast<int *>(flow);
    *(flowInt + 94) = idx;
}

/* Mark a stack as end.
 * Ultimately, `analyzer` will have a `private_stack` member 
 */
void stack_end(uint64_t flow)
{
#ifdef DEBUG_MSGS
    fprintf(stderr, "[Fini] Marking end of stack #%d\n", CurrStack);
#endif
    assert(CurrStack >= 0);
    available_vector &= ~((uint64_t)1 << (MAX_STACK_NUM - 1 - CurrStack));
    /* if this packet is not associated with any flow, just return */
    if (!flow)
        return;
    int flowIdx = get_key_from_flow_ptr(flow);
    /* since this flow still has packets left, vec is always non-zero */
    int currPkt = __builtin_clzl(seenFlow[flowIdx]);
    assert((CurrStack == currPkt) && "Current packet not the first packet of flow?");
    seenFlow[flowIdx] &= ~((uint64_t)1 << (MAX_STACK_NUM - 1 - CurrStack));
    /* mark the flow as not seen when we finish processing a flow
     * TODO: check whether multiple unconditional set, or 1 conditional set, is faster
     */
    if (!seenFlow[flowIdx])
        set_key_to_flow_ptr(flow, -1);
#ifdef DEBUG_MSGS
    if (CurrStack + 1 == NumStacks)
        processedPkts += NumStacks;
#endif
}

static inline uint64_t get_curr_pkt_vec()
{
    assert(CurrStack >= 0);
    return (uint64_t)1 << (MAX_STACK_NUM - 1 - CurrStack);
}

// static void stack_disable()
// {
// #ifdef DEBUG_MSGS
//     fprintf(stderr, "Marking stack #%d as unavailable\n", CurrStack);
// #endif
//     available_vector &= ~((uint64_t)1 << (MAX_STACK_NUM - 1 - CurrStack));
// #ifdef DEBUG_MSGS
//     fprintf(stderr, "available vector afterwards: %lx\n", available_vector);
// #endif
// }

/* type 1 SP get_next: simple RR */
static inline int get_next_packet_1()
{
    return (CurrStack + 1) % NumStacks;
}

/* RR the next stack, according to vector */
static inline int non_zero_rr(uint64_t vec)
{
    if (unlikely(!vec))
        return -1;
    int ls = get_next_packet_1();
    uint64_t moved = (vec << ls) >> ls;
    return moved ? __builtin_clzl(moved) : __builtin_clzl(vec);
}

/* type 2 SP get_next: picking first packet of each flow */
static inline int get_next_packet_2()
{
    int ret;
    /* if there is still flow pending, move to the next stack to make flows */
    if (!all_flows_initialized) {
        /* all previous packets have no flow-level processing,
         * we have no choice but classic finish vector
         * note that available_vector is guaranteed to be non-zero
         */
        // ret = __builtin_clzl(available_vector);
        ret = non_zero_rr(available_vector);
#ifdef DEBUG_MSGS
    // fprintf(stderr, "[type 2] Switching from #%d to #%d (pre-initialized)\n", CurrStack, (CurrStack + 1 == NumStacks) ? ret : CurrStack + 1);
    fprintf(stderr, "[type 2] Switching from #%d to #%d (pre-initialized)\n", CurrStack, ret);
#endif
        // return (CurrStack + 1 == NumStacks) ? ret : CurrStack + 1;
        return ret;
    }
    /* if no flow pending and left, we are clear to go */
    if (!seenFlowSize) {
#ifdef DEBUG_MSGS
    fprintf(stderr, "[type 2] Switching from #%d to #%d (empty flow)\n", CurrStack, -1);
#endif
        return -1;
    }

    if (unlikely(!redoQueue.empty())) {
        int to = redoQueue[redoIdx++];
        if (redoIdx == redoQueue.size())
            redoQueue.clear();
        return to;
    }
    
    /* else, RR all active flows to make PL */
    unsigned threshold = flowIdxCtr + seenFlowSize;
    /* TODO: fast path when there is only one flow */
    do {
        /* all flows could not find a packet */
        if (unlikely(flowIdxCtr == threshold)) {
#ifdef DEBUG_MSGS
    fprintf(stderr, "[type 2] flow table depleted, switching to main stack\n");
#endif
            return -1;
        }
        uint64_t thisVec = seenFlow[flowIdxCtr % seenFlowSize];
        flowIdxCtr++;
        // ret = (it->second == 0) ? -1 : __builtin_clzl(it->second);
        ret = __builtin_clzl(thisVec);
        /* when flow vec is non-zero, clz returns valid output */
        if (thisVec)
            break;
    // } while (ret == -1);
    } while (true);

#ifdef DEBUG_MSGS
    fprintf(stderr, "[type 2] Switching from #%d to #%d (Counter: %u, flow num: %u)\n", CurrStack, ret, flowIdxCtr - 1, seenFlowSize);
    fprintf(stderr, "Vector of each flow:\n");
    for (int i = 0; i < seenFlowSize; i++) {
        fprintf(stderr, "\t%lx (%d)\n", seenFlow[i], (seenFlow[i] == 0) ? -1 : __builtin_clzl(seenFlow[i]));
    }
#endif

    return ret;
}

void stack_next_0()
{
    /* return to main stack if initialization of all stacks not done */
    int to = ((CurrStack + 1) == NumStacks) ? 0 : -1;
    /* under very, very rare conditions, stack 0 is a malformed packet,
     * which prohibits switching there
     * TODO: this is still vulnerable when all packets in a batch is malformed
     * TODO: switch to non_zero_rr, but that might be slow
     */
    if (unlikely(__builtin_clzl(available_vector)))
        to = __builtin_clzl(available_vector);
#ifdef DEBUG_MSGS
    fprintf(stderr, "[Init] Starting stack #%d, switching to %d (total pkts: %ld)\n", CurrStack, to, processedPkts + CurrStack + 1);
#endif
    stack_switch(CurrStack, to);
}

void stack_next_1()
{
    int to = get_next_packet_1();
#ifdef DEBUG_MSGS
    fprintf(stderr, "[Type 1] Switching from #%d to #%d\n", CurrStack, to);
#endif
    stack_switch(CurrStack, to);
}

void stack_next_2()
{
    int to = get_next_packet_2();
// #ifdef DEBUG_MSGS
//     fprintf(stderr, "[Type 2] Switching from #%d to #%d\n", CurrStack, to);
// #endif
    stack_switch(CurrStack, to);
}

/* note that we should also set persistent flow key upon flow start */
void mark_flow_start(uint64_t flow)
{
    int key = get_key_from_flow_ptr(flow);

    /* -1 is used as default value
     * TODO: check if this slows down flow init
     * note that flow key must be rewritten, whether the flow is in FT or not
     */
    if (key < 0)
        key = seenFlowSize++;
    set_key_to_flow_ptr(flow, key);

    seenFlow[key] |= (uint64_t)1 << (MAX_STACK_NUM - 1 - CurrStack);
    
    /* This is a tricky location: this function could be executed by
     * both normal and redo situations. So redoQueue is introduced
     * to separate the two.
     */
    int to;
    if (unlikely(!redoQueue.empty())) {
        to = redoQueue[redoIdx++];
        if (redoIdx == redoQueue.size()) {
            redoIdx = 0;
            redoQueue.clear();
        }
    }
    else {
        /* RR, but bypass all finished stacks */
        // to = get_next_packet_1();
        // uint64_t tmpVec = (available_vector << to) >> to;
        // to = (tmpVec == 0) ? __builtin_clzl(available_vector) : __builtin_clzl(tmpVec);
        
        /* TODO: non zero rr might be slow */
        to = non_zero_rr(available_vector);
    }
#ifdef DEBUG_MSGS
    fprintf(stderr, "[flow_start] Switching from #%d to #%d\n", CurrStack, to);
#endif
    stack_switch(CurrStack, to);
}

void mark_flow_end(uint64_t flow)
{
    /* all packets finished under batch size 64 */
    if (unlikely(available_vector == 0))
        return;
    /* during snort fini, there is not a single stack available */
    if (unlikely(__builtin_clzl(available_vector) >= NumStacks)) {
        return;
    }
    // assert(redoAddr && "Set redo address before marking end of flow!");
    /* by looking up the hash table, we get the packets from the same flow */
    int key = get_key_from_flow_ptr(flow);
    uint64_t pktVec = seenFlow[key];
    assert(pktVec != 0);
    int nextPkt;
    while (pktVec && 
            ((nextPkt = __builtin_clzl(pktVec)) < NumStacks)) {
        /* note that pkt index from 1 while stack is from 0 */
        if (nextPkt != CurrStack) {
            /* now we save the whole stack, and restore it when necessary
             * TODO: in theory, we only need RIP and several caller saved reg
             * to make this work. Doing that will free us from one time force 
             * saving.
             */
            /* rip is at offset 1 */
            // CalleeRegs[nextPkt][1] = redoAddr;
            /* overwrite original stack with the pre-lookup copy,
             * in this way, when we switch back to this stack again,
             * it will be the pre-loopup position
             */
#ifdef DEBUG_MSGS
    fprintf(stderr, "[flow_end] rebasing stack #%d\n", nextPkt);
#endif
            memcpy(CalleeRegs[nextPkt], RestoreRegs[nextPkt], sizeof(RegSet));
            redoQueue.emplace_back(nextPkt);
            /* remove all pending packets in the flow..
             * they will create a new one if needed
             */
            seenFlow[key] &= ~((uint64_t)1 << (MAX_STACK_NUM - 1 - nextPkt));
        }
        pktVec &= ~((uint64_t)1 << (MAX_STACK_NUM - 1 - nextPkt));
    }
    /* note we should prevent the stacks to be redo multiple times
     * but since flow remove is quite rare, the chance for it to happen is low
     */
}

void stack_save()
{
    SaveStack(&RestoreRegs[CurrStack]);
}