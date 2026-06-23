// stubs/freertos/task.h — HOST-ONLY FreeRTOS task/critical-section stub.
// globals.h pulls <freertos/task.h> for TaskHandle_t and the dual-core task
// handles. The render harness runs single-threaded on host: task creation is a
// no-op and critical sections are no-ops (matches tempo_replay's portMUX stub).
// NON-SHIPPING.
#pragma once
#include <cstdint>

typedef void* TaskHandle_t;
typedef void* QueueHandle_t;
typedef void* SemaphoreHandle_t;
typedef uint32_t TickType_t;
typedef int BaseType_t;
typedef unsigned int UBaseType_t;
typedef void (*TaskFunction_t)(void*);

#define pdTRUE 1
#define pdFALSE 0
#define pdPASS 1
#define pdMS_TO_TICKS(ms) (ms)
#define portMAX_DELAY 0xffffffffUL
#define tskNO_AFFINITY 0x7fffffff

// --- critical sections (no-op on a single-threaded host) -------------------
#ifndef portMUX_TYPE
typedef struct { int dummy; } portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED { 0 }
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
static inline void portENTER_CRITICAL_ISR(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL_ISR(portMUX_TYPE*) {}
static inline void vPortCPUInitializeMutex(portMUX_TYPE*) {}
#endif

// --- task API (never spun up on host) --------------------------------------
static inline BaseType_t xTaskCreatePinnedToCore(TaskFunction_t, const char*, uint32_t,
                                                 void*, UBaseType_t, TaskHandle_t*, BaseType_t) { return pdPASS; }
static inline BaseType_t xTaskCreate(TaskFunction_t, const char*, uint32_t,
                                     void*, UBaseType_t, TaskHandle_t*) { return pdPASS; }
static inline void vTaskDelay(TickType_t) {}
static inline void vTaskDelete(TaskHandle_t) {}
static inline TaskHandle_t xTaskGetCurrentTaskHandle() { return nullptr; }
static inline UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t) { return 0; }
