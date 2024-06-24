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
extern unsigned NumStacks;

/* Q: create stack now happens in another module, so this has to be non-static */
extern RegSet DefaultStack;
extern void *StackTops[MAX_STACK_NUM];
extern int CurrStack;
extern unsigned ReservedStacks;
extern void* pkt_buffer[MAX_STACK_NUM];

/* public interfaces */
void init_stacks();
void init_switchers(void *);
void set_private_switcher();
void reserve_stacks(unsigned num);
// bool process_packet_with_stack(snort::Packet *p);
void stack_switch(int from, int to);
void stack_next();
void stack_back();
void stack_end();
void stack_lock();
void stack_unlock();
bool stack_finished(int idx);
// int get_unfinished_stack();
int get_unfinished_stack(int curr);
bool all_stacks_finished();
extern bool priv_stk_ret;

/* asm interfaces */
extern void StackSwitchAsm(RegSet *src, RegSet *dst);
extern int SaveStack(RegSet *regs);
extern void RestoreStack(RegSet *regs);

}

/* prefetch a variable from the next stack 
 * FIXME: not limit to packet-related variables
 */
#define stack_next_prefetch(var_to_prefetch)\
do { \
    int to = get_unfinished_stack(CurrStack);\
    asm volatile ( \
        "prefetcht0 %[p]" : : [p] "m" \ 
        (*reinterpret_cast<const volatile char *>( \
                reinterpret_cast<Packet *>(pkt_buffer[(CurrStack+1) % NumStacks])->var_to_prefetch \
            ) \
        ) \
    ); \
    stack_switch(CurrStack, to); \
} while (0) \

#define register_packet(p) \
do { \
    pkt_buffer[CurrStack] = p; \
} while (0) \

#endif