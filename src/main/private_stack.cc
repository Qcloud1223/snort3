#include <stdio.h>

#include "private_stack.h"

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
}

void stack_switch(unsigned from, unsigned to)
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

void stack_end()
{
    CurrStack++;
    int to = CurrStack == NumStacks ? -1 : CurrStack;
    printf("Finishing Stack #%d\n", to);
    stack_switch(CurrStack - 1, to);
}

void destroy_stacks()
{
    NumStacks = 0;
}