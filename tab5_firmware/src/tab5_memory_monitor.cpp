#include "tab5_memory_monitor.h"

#include <algorithm>
#include <cmath>

#include <esp_heap_caps.h>
#include <esp_log.h>
#include <esp_psram.h>

namespace tab5 {

namespace {
static constexpr const char* TAG = "Tab5Mem";
static constexpr uint32_t kPollIntervalMs = 5000;
}

MemoryMonitor& MemoryMonitor::instance()
{
  static MemoryMonitor monitor;
  return monitor;
}

MemoryMonitor::Sample MemoryMonitor::sample_dram() const
{
  const uint32_t caps = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
  Sample s{};
  s.total    = heap_caps_get_total_size(caps);
  s.free     = heap_caps_get_free_size(caps);
  s.min_free = heap_caps_get_minimum_free_size(caps);
  s.used     = s.total > s.free ? (s.total - s.free) : 0;
  return s;
}

MemoryMonitor::Sample MemoryMonitor::sample_spiram() const
{
#ifdef MALLOC_CAP_SPIRAM
  const uint32_t caps = MALLOC_CAP_SPIRAM;
#else
  const uint32_t caps = 0;
#endif
  Sample s{};
  if (caps != 0) {
    s.total    = heap_caps_get_total_size(caps);
    s.free     = heap_caps_get_free_size(caps);
    s.min_free = heap_caps_get_minimum_free_size(caps);
    s.used     = s.total > s.free ? (s.total - s.free) : 0;
  }
  return s;
}

void MemoryMonitor::log_sample(const char* label,
                               size_t dram_used,
                               size_t dram_free,
                               size_t dram_total,
                               size_t spiram_used,
                               size_t spiram_free,
                               size_t spiram_total) const
{
  ESP_LOGI(TAG,
           "%s | DRAM used=%zuKB free=%zuKB total=%zuKB | SPIRAM used=%zuKB free=%zuKB total=%zuKB",
           label,
           dram_used / 1024,
           dram_free / 1024,
           dram_total / 1024,
           spiram_used / 1024,
           spiram_free / 1024,
           spiram_total / 1024);
}

void MemoryMonitor::log_boot_summary() const
{
  Sample dram   = sample_dram();
  Sample spiram = sample_spiram();
  log_sample("boot", dram.used, dram.free, dram.total,
             spiram.used, spiram.free, spiram.total);

  size_t psram_size = esp_psram_get_size();
  ESP_LOGI(TAG, "PSRAM reported size=%zuMB", psram_size / (1024 * 1024));

#ifdef CONFIG_SPIRAM_SPEED
  ESP_LOGI(TAG, "Configured PSRAM speed=%dMHz", CONFIG_SPIRAM_SPEED);
#endif

#if defined(CONFIG_SPIRAM_XIP_FROM_PSRAM) && CONFIG_SPIRAM_XIP_FROM_PSRAM
#error "XiP from PSRAM must remain disabled for Tab5"
#endif

#ifdef CONFIG_SPIRAM_XIP_FROM_PSRAM
  ESP_LOGW(TAG, "CONFIG_SPIRAM_XIP_FROM_PSRAM defined; ensure release disables XiP");
#else
  ESP_LOGI(TAG, "XiP from PSRAM: disabled");
#endif
}

void MemoryMonitor::init()
{
  if (initialized_) return;

  if (!esp_psram_is_initialized()) {
    ESP_LOGW(TAG, "PSRAM is not initialised; skipping instrumentation");
  }

  Sample dram   = sample_dram();
  Sample spiram = sample_spiram();

  baseline_dram_used_   = dram.used;
  baseline_spiram_used_ = spiram.used;
  peak_dram_used_       = dram.used;
  peak_spiram_used_     = spiram.used;
  last_poll_ms_         = 0;
  baseline_ready_       = false;

  log_boot_summary();

  ESP_LOGI(TAG, "Budgets -> SPIRAM <= %zuKB, DIRAM <= %.0f%%", budget_.spiram_budget_bytes / 1024,
           budget_.diram_budget_ratio * 100.0f);

  initialized_ = true;
}

void MemoryMonitor::check_budgets(const Sample& dram, const Sample& spiram, bool host_alive)
{
  if (spiram.used > budget_.spiram_budget_bytes && spiram.total != 0) {
    ESP_LOGE(TAG, "SPIRAM budget exceeded: used=%zuKB limit=%zuKB",
             spiram.used / 1024, budget_.spiram_budget_bytes / 1024);
  }

  if (dram.total > 0) {
    float dram_usage_ratio = static_cast<float>(dram.used) / static_cast<float>(dram.total);
    if (dram_usage_ratio > budget_.diram_budget_ratio) {
      ESP_LOGW(TAG, "DIRAM usage high: %.1f%% (limit %.0f%%)",
               dram_usage_ratio * 100.0f, budget_.diram_budget_ratio * 100.0f);
    }
  }

  if (!host_alive) {
    auto diff_spiram = static_cast<float>(static_cast<int64_t>(spiram.used) -
                                          static_cast<int64_t>(baseline_spiram_used_));
    auto diff_dram = static_cast<float>(static_cast<int64_t>(dram.used) -
                                        static_cast<int64_t>(baseline_dram_used_));
    float spiram_drift = spiram.total ? std::fabs(diff_spiram) / static_cast<float>(spiram.total) * 100.0f : 0.0f;
    float dram_drift   = dram.total ? std::fabs(diff_dram) / static_cast<float>(dram.total) * 100.0f : 0.0f;

    if (spiram_drift > budget_.drift_limit_percent) {
      ESP_LOGW(TAG, "Idle SPIRAM drift %.2f%% exceeds %.2f%%", spiram_drift, budget_.drift_limit_percent);
    }
    if (dram_drift > budget_.drift_limit_percent) {
      ESP_LOGW(TAG, "Idle DIRAM drift %.2f%% exceeds %.2f%%", dram_drift, budget_.drift_limit_percent);
    }
  }
}

void MemoryMonitor::poll(uint32_t now_ms, bool host_alive)
{
  if (!initialized_) return;
  if (last_poll_ms_ != 0 && (now_ms - last_poll_ms_) < kPollIntervalMs) return;

  Sample dram   = sample_dram();
  Sample spiram = sample_spiram();

  if (!baseline_ready_) {
    baseline_dram_used_   = dram.used;
    baseline_spiram_used_ = spiram.used;
    peak_dram_used_       = dram.used;
    peak_spiram_used_     = spiram.used;
    baseline_ready_       = true;
    last_poll_ms_         = now_ms;
    log_sample("baseline", dram.used, dram.free, dram.total,
               spiram.used, spiram.free, spiram.total);
    return;
  }

  peak_dram_used_   = std::max(peak_dram_used_, dram.used);
  peak_spiram_used_ = std::max(peak_spiram_used_, spiram.used);

  log_sample("tick", dram.used, dram.free, dram.total,
             spiram.used, spiram.free, spiram.total);

  check_budgets(dram, spiram, host_alive);

  last_poll_ms_ = now_ms;
}

}  // namespace tab5
