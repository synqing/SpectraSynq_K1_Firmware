#pragma once
#include <stdint.h>
#define RMT_TX_MODE 0
#define RMT_MEM_NUM_BLOCKS_1 1
#define RMT_WAIT_FOR_EVER 0
typedef struct { uint8_t level0; uint16_t duration0; uint8_t level1; uint16_t duration1; } rmt_data_t;
static inline bool rmtInit(int,int,int,uint32_t){return true;} static inline void rmtSetEOT(int,int){} static inline bool rmtWrite(int, rmt_data_t*, size_t, int){return true;}
