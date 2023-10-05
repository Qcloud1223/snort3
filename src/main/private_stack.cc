#include <stdio.h>
#include <stdint.h>

#include "private_stack.h"

RegSet DefaultStack;
void *StackTops[MAX_STACK_NUM];
int CurrStack = 0;
unsigned ReservedStacks = 0;

static int finished_idx = -1;
static uint64_t finished_vector;
static bool all_stacks_initialized = false;


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
    assert(num <= MAX_STACK_NUM);
    NumStacks = num;
    ReservedStacks = 0;
    finished_idx = -1;
    all_stacks_initialized = false;
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

/* Get the next stack with policy.
 * TODO: actually make the policy in user's code, by allowing defining a 
 * function to make the decision, based on the context
 */
/* TODO: a better name of this function should be `yield_control` */
void stack_next()
{
    /* if we reach the first private stack again, all the stacks are initialized */
    /* WARNING: this is still packet-based, not context-based! */
    if (ReservedStacks != 1 && CurrStack == 0)
        all_stacks_initialized = true;
    /* first, create all the stacks by naively going back to main */
    if (all_stacks_initialized == false) {
        CurrStack++;
        // fprintf(stderr, "[Init] Switching from %d to %d\n", CurrStack - 1, -1);
        stack_switch(CurrStack - 1, -1);
    }
    /* next, finish any unfinished stack */
    int to = get_unfinished_stack();
    // fprintf(stderr, "[Fin] Switching from %d to %d\n", CurrStack, to);
    stack_switch(CurrStack, to);
}

/* Mark a stack as end.
 * Ultimately, `analyzer` will have a `private_stack` member 
 */
void stack_end()
{
    // fprintf(stderr, "Ending stack #%d\n", CurrStack);
    assert(CurrStack >= 0);
    finished_vector |= ((uint64_t)1 << CurrStack);
}

bool all_stacks_finished()
{
    uint64_t fin_vec = ~(uint64_t)0 >> (64 - ReservedStacks);
    return finished_vector == fin_vec;
}

bool stack_finished(int idx)
{
    return (finished_vector & ((uint64_t)1 << idx)) != 0;
}

/* return pending stack index if any, -1 if none */
int get_unfinished_stack()
{
    /* TODO: get unfinished with policy. Now is round-robin */
    uint8_t i;
    for (i = 0; i < ReservedStacks; i++) {
        if ((finished_vector & ((uint64_t)1 << i)) == (uint64_t)0) {
            // fprintf(stderr, "Find unfinished stack %d\n", i);
            return i;
        } 
    }
    return -1;
}