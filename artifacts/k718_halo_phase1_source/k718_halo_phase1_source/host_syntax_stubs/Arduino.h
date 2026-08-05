#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
uint32_t millis(void); uint32_t micros(void); void delay(int); void delayMicroseconds(int); void vTaskDelay(int);
struct Serial_t { template<typename... Args> void printf(const char*, Args...) {} void println(const char*) {} void begin(int) {} }; extern Serial_t Serial;
struct ESP_t { uint32_t getFreeHeap(){return 0;} uint32_t getFreePsram(){return 0;} }; extern ESP_t ESP;
#define OUTPUT 1
#define LOW 0
void pinMode(int,int); void digitalWrite(int,int);
