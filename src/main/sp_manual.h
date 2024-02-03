/* header for manually crafted function calls */
#pragma once

#include <iostream>

void topLevelInit(std::string spFilename, std::string rwFilename);
void yieldControlFirst();
void yieldControlLast();
void reserve_stacks(unsigned batchSize);

#define batchInit() \
    bootstrapSPQueue();\
    SaveStack(&DefaultStack);\
    asm volatile ("" ::: "memory");

#define pktInit() \
    asm volatile( \
            "movq %0, %%rsp " \
            :                 \
            : "rm"(StackTops[ReservedStacks]) \
            : \
        ); \
    CurrStack = ReservedStacks++;

#define MAX_STACK_NUM 64
typedef void *RegSet[9];
void bootstrapSPQueue();
extern void *StackTops[MAX_STACK_NUM];
extern int CurrStack;
extern unsigned ReservedStacks;
extern RegSet DefaultStack;
extern "C" int SaveStack(RegSet *regs);
