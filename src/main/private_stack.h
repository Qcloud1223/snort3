#ifndef _PRIV_STK
#define _PRIV_STK

#include <stdlib.h>
#include <assert.h>
#include <stdint.h>
#include <unordered_map>
#include <vector>

/* IMPORTANT: tell the compiler: don't mangle the following name for me */
extern "C" { 

typedef void *RegSet[9];
#define MAX_STACK_NUM 64
#define MAX_STACK_SIZE ((1 << 23))
extern RegSet RestoreRegs[MAX_STACK_NUM];
static RegSet CalleeRegs[MAX_STACK_NUM];
static unsigned NumStacks;

/* Q: create stack now happens in another module, so this has to be non-static */
extern RegSet DefaultStack;
extern void *StackTops[MAX_STACK_NUM];
extern int CurrStack;
extern unsigned ReservedStacks;
extern bool all_flows_initialized;
/* TODO: previous-rip only solution */
// extern void *redoAddr;

/* public interfaces */
void init_stacks();
void reserve_stacks(unsigned num);
// bool process_packet_with_stack(snort::Packet *p);
void stack_switch(int from, int to);
void stack_next_0();
void stack_next_1();
void stack_next_2(int spIdx);
void stack_next_2_final(int spIdx);
void stack_end(uint64_t flow);
/* mark the lookup and remove of flow */
void mark_flow_start(uint64_t flow);
void mark_flow_end(uint64_t flow);
/* inline to prevent multiple definition */
// inline void set_redo_addr(void *addr) {redoAddr = addr;}

/* asm interfaces */
extern void StackSwitchAsm(RegSet *src, RegSet *dst);
extern int SaveStack(RegSet *regs);
extern void RestoreStack(RegSet *regs);

}

#endif