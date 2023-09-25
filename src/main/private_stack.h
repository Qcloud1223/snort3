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
static RegSet DefaultStack;
static void *StackTops[MAX_STACK_NUM];

static unsigned NumStacks;
static unsigned CurrStack = 0;

/* public interfaces */
void init_stacks();
void reserve_stacks(unsigned num);
// bool process_packet_with_stack(snort::Packet *p);
void stack_switch(unsigned from, unsigned to);
void stack_next();
void stack_end();
void destroy_stacks();
extern bool priv_stk_ret;

/* asm interfaces */
extern void StackSwitchAsm(RegSet *src, RegSet *dst);
extern int SaveStack(RegSet *regs);
extern void RestoreStack(RegSet *regs);

}

#endif