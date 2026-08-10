#pragma once

#include <cstdint>
#include <cstddef>

namespace tab5 {

class MemoryMonitor {
public:
  static MemoryMonitor& instance();

  void init();
  void poll(uint32_t now_ms, bool host_alive);

private:
  MemoryMonitor() = default;
  void log_boot_summary() const;
  void log_sample(const char* label, size_t dram_used, size_t dram_free,
                  size_t dram_total, size_t spiram_used, size_t spiram_free,
                  size_t spiram_total) const;

  struct BudgetConfig {
    size_t spiram_budget_bytes = 24u * 1024u * 1024u; // 24MB external framebuffer budget
    float diram_budget_ratio   = 0.70f;              // DIRAM usage ≤ 70%
    float drift_limit_percent  = 1.0f;               // allowable leak drift
  };

  struct Sample {
    size_t used  = 0;
    size_t free  = 0;
    size_t total = 0;
    size_t min_free = 0;
  };

  Sample sample_dram() const;
  Sample sample_spiram() const;
  void check_budgets(const Sample& dram, const Sample& spiram, bool host_alive);

  BudgetConfig budget_{};
  size_t baseline_dram_used_ = 0;
  size_t baseline_spiram_used_ = 0;
  size_t peak_dram_used_ = 0;
  size_t peak_spiram_used_ = 0;
  uint32_t last_poll_ms_ = 0;
  bool baseline_ready_ = false;
  bool initialized_ = false;
};

}  // namespace tab5
