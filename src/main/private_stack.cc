#include <stdio.h>

#include "private_stack.h"

RegSet DefaultStack;
void *StackTops[MAX_STACK_NUM];
int CurrStack = 0;
unsigned ReservedStacks = 0;

static int finished_idx = -1;

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

void stack_next()
{
    CurrStack++;
    int to = CurrStack == NumStacks ? 0 : CurrStack;
    printf("Preparing switching to Stack #%d\n", to);
    stack_switch(CurrStack - 1, to);
}

void stack_back()
{
    CurrStack++;
    // printf("Stack #%d switching back to main\n", CurrStack - 1);
    stack_switch(CurrStack - 1, -1);
}

void stack_end()
{
    CurrStack++;
    /* finished idx is always initialized as -1 */
    finished_idx++;
    int to = CurrStack == NumStacks ? -1 : CurrStack;
    // printf("Finishing Stack #%d\n", to);
    stack_switch(CurrStack - 1, to);
}

bool stack_finished(int idx)
{
    return finished_idx >= idx;
}