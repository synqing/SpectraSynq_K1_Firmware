// FS.h — HOST-ONLY in-memory filesystem stub (non-shipping). See LittleFS.h.
// Plain C storage only: firmware TUs include this after stubs/Arduino.h, whose
// min/max macros break the C++ standard containers.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef FILE_READ
#define FILE_READ "r"
#endif
#ifndef FILE_WRITE
#define FILE_WRITE "w"
#endif
#ifndef FILE_APPEND
#define FILE_APPEND "a"
#endif

#define K1_HOST_FS_FILES 24
#define K1_HOST_FS_PATH 48
#define K1_HOST_FS_BYTES 40000

struct K1HostFsEntry {
  bool used;
  char path[K1_HOST_FS_PATH];
  size_t len;
  uint8_t data[K1_HOST_FS_BYTES];
};

inline K1HostFsEntry k1_host_fs_table[K1_HOST_FS_FILES] = {};
inline unsigned k1_host_fs_writes = 0;  // non-empty write() calls

static inline K1HostFsEntry *k1_host_fs_find(const char *path) {
  for (int i = 0; i < K1_HOST_FS_FILES; i++) {
    if (k1_host_fs_table[i].used && strcmp(k1_host_fs_table[i].path, path) == 0) {
      return &k1_host_fs_table[i];
    }
  }
  return nullptr;
}

static inline K1HostFsEntry *k1_host_fs_create(const char *path) {
  K1HostFsEntry *e = k1_host_fs_find(path);
  if (e == nullptr) {
    for (int i = 0; i < K1_HOST_FS_FILES && e == nullptr; i++) {
      if (!k1_host_fs_table[i].used) e = &k1_host_fs_table[i];
    }
    if (e == nullptr) return nullptr;
    e->used = true;
    strncpy(e->path, path, K1_HOST_FS_PATH - 1);
    e->path[K1_HOST_FS_PATH - 1] = '\0';
  }
  return e;
}

// Test helpers.
static inline bool k1_host_fs_put(const char *path, const uint8_t *bytes, size_t n) {
  K1HostFsEntry *e = k1_host_fs_create(path);
  if (e == nullptr || n > K1_HOST_FS_BYTES) return false;
  memcpy(e->data, bytes, n);
  e->len = n;
  return true;
}
static inline void k1_host_fs_reset() {
  memset(k1_host_fs_table, 0, sizeof(k1_host_fs_table));
  k1_host_fs_writes = 0;
}

class File {
 public:
  File() {}
  File(K1HostFsEntry *e, bool writing) : e_(e), writing_(writing) {}
  explicit operator bool() const { return e_ != nullptr; }
  size_t size() const { return e_ ? e_->len : 0; }
  bool seek(uint32_t pos) {
    if (!e_ || pos > e_->len) return false;
    pos_ = pos;
    return true;
  }
  int available() { return e_ ? (int)(e_->len - pos_) : 0; }
  int read() {
    if (!e_ || pos_ >= e_->len) return -1;
    return e_->data[pos_++];
  }
  size_t read(uint8_t *buf, size_t n) {
    if (!e_) return 0;
    const size_t left = e_->len - pos_;
    const size_t k = n < left ? n : left;
    if (k) memcpy(buf, e_->data + pos_, k);
    pos_ += k;
    return k;
  }
  size_t write(const uint8_t *buf, size_t n) {
    if (!e_ || !writing_ || pos_ + n > K1_HOST_FS_BYTES) return 0;
    memcpy(e_->data + pos_, buf, n);
    pos_ += n;
    if (pos_ > e_->len) e_->len = pos_;
    if (n) k1_host_fs_writes++;
    return n;
  }
  size_t write(uint8_t b) { return write(&b, 1); }
  void flush() {}
  void close() { e_ = nullptr; }

 private:
  K1HostFsEntry *e_ = nullptr;
  bool writing_ = false;
  size_t pos_ = 0;
};

class HostLittleFS {
 public:
  bool begin(bool = false) { return true; }
  File open(const char *path, const char *mode = FILE_READ) {
    const bool w = mode && (mode[0] == 'w' || mode[0] == 'a' || strchr(mode, '+'));
    if (w) {
      if (mode[0] == 'r' && !k1_host_fs_find(path)) return File();
      K1HostFsEntry *e = k1_host_fs_create(path);
      File f(e, true);
      if (e && mode[0] == 'w') e->len = 0;
      if (e && mode[0] == 'a') f.seek((uint32_t)e->len);
      return f;
    }
    return File(k1_host_fs_find(path), false);
  }
  bool exists(const char *path) { return k1_host_fs_find(path) != nullptr; }
  bool remove(const char *path) {
    K1HostFsEntry *e = k1_host_fs_find(path);
    if (!e) return false;
    memset(e, 0, sizeof(*e));
    return true;
  }
  bool rename(const char *from, const char *to) {
    K1HostFsEntry *e = k1_host_fs_find(from);
    if (!e) return false;
    remove(to);
    strncpy(e->path, to, K1_HOST_FS_PATH - 1);
    return true;
  }
  bool mkdir(const char *) { return true; }
  size_t totalBytes() { return 1u << 20; }
  size_t usedBytes() { return 0; }
};

inline HostLittleFS LittleFS;
