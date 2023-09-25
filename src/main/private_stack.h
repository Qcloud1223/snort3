#ifndef _PRIV_STK
#define _PRIV_STK

#include <stdlib.h>
#include <assert.h>

/* IMPORTANT: tell the compiler: don't mangle the following name for me */
extern "C" { 

typedef void *RegSet[9];
#define MAX_STACK_NUM 64
#define MAX_STACK_SIZE ((1 << 23))
static RegSet CalleeRegs[MAX_STACK_NUM];
static unsigned NumStacks;

/* Q: create stack now happens in another module, so this has to be non-static */
extern RegSet DefaultStack;
extern void *StackTops[MAX_STACK_NUM];
extern int CurrStack;
extern unsigned ReservedStacks;

/* public interfaces */
void init_stacks();
void reserve_stacks(unsigned num);
// bool process_packet_with_stack(snort::Packet *p);
void stack_switch(int from, int to);
void stack_next();
void stack_back();
void stack_end();
bool stack_finished(int idx);
extern bool priv_stk_ret;

/* asm interfaces */
extern void StackSwitchAsm(RegSet *src, RegSet *dst);
extern int SaveStack(RegSet *regs);
extern void RestoreStack(RegSet *regs);

}

#endif