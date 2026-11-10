// CDC serial port, PRSM packet, and K1CT frame helpers.
// Extracted from tools/intent_cdc_stream.js for reuse by playback engine and editor.
// Zero external dependencies — Node built-ins only.

import fs from "node:fs";
import { execSync } from "node:child_process";

// ---------------------------------------------------------------------------
// PRSM packet construction (34 bytes, little-endian)
// ---------------------------------------------------------------------------

function writeU64LE(buf, off, value) {
  const lo = value >>> 0;
  const hi = Math.floor(value / 4294967296) >>> 0;
  buf.writeUInt32LE(lo, off);
  buf.writeUInt32LE(hi, off + 4);
}

/**
 * Build a 34-byte PRSM FeatureFrame packet.
 * @param {{ hz: number, seq: number, t_us: number, prim8_u16: number[] }} opts
 * @returns {Buffer}
 */
export function makePrsmPacket({ hz, seq, t_us, prim8_u16 }) {
  const buf = Buffer.alloc(34);
  buf.write("PRSM", 0, 4, "ascii");
  buf.writeUInt8(1, 4);           // version
  buf.writeUInt8(hz & 0xff, 5);   // hz
  buf.writeUInt32LE(seq >>> 0, 6);
  writeU64LE(buf, 10, t_us);

  let o = 18;
  for (let i = 0; i < 8; i++) {
    const v = prim8_u16[i] ?? 0;
    buf.writeUInt16LE(v & 0xffff, o);
    o += 2;
  }
  return buf;
}

// ---------------------------------------------------------------------------
// K1CT frame construction (fire-and-forget PARAM_SET)
// ---------------------------------------------------------------------------

// Pre-computed CRC-32 lookup table (IEEE polynomial 0xEDB88320).
const CRC32_TABLE = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let j = 0; j < 8; j++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
  CRC32_TABLE[i] = c;
}

function crc32(buf, offset = 0, length = buf.length - offset) {
  let crc = 0xFFFFFFFF;
  for (let i = offset; i < offset + length; i++) {
    crc = CRC32_TABLE[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

const K1CT_MAGIC = Buffer.from("K1CT", "ascii");
const K1CT_VERSION = 0x01;
const K1CT_CMD_PARAM_SET = 0x11;

/**
 * Build a K1CT PARAM_SET frame (fire-and-forget).
 * Frame: magic(4) + version(1) + msg_type(1) + payload_len(u16 LE) + payload(6) + CRC-32(4) = 18 bytes.
 * CRC covers Version..Payload (NOT magic bytes).
 * @param {number} paramId - u16 parameter ID
 * @param {number} value   - u32 parameter value
 * @returns {Buffer} 18-byte K1CT frame
 */
export function makeK1ctParamSet(paramId, value) {
  // Header: magic(4) + version(1) + type(1) + len(2) = 8 bytes
  // Payload: param_id(2) + value(4) = 6 bytes
  // CRC: 4 bytes
  const buf = Buffer.alloc(18);
  K1CT_MAGIC.copy(buf, 0);
  buf.writeUInt8(K1CT_VERSION, 4);
  buf.writeUInt8(K1CT_CMD_PARAM_SET, 5);
  buf.writeUInt16LE(6, 6); // payload length = 6 bytes

  buf.writeUInt16LE(paramId & 0xFFFF, 8);
  buf.writeUInt32LE(value >>> 0, 10);

  // CRC covers bytes [4..14) — version(1) + type(1) + len(2) + payload(6) = 10 bytes
  const checksum = crc32(buf, 4, 10);
  buf.writeUInt32LE(checksum, 14);

  return buf;
}

// ---------------------------------------------------------------------------
// Serial port helpers (macOS, zero deps)
// ---------------------------------------------------------------------------

/**
 * Open a CDC serial port in raw mode.
 * @param {string} portPath - e.g. "/dev/cu.usbmodemK1_00014"
 * @returns {number} file descriptor
 */
export function openCdcPort(portPath) {
  execSync(`stty -f ${portPath} raw -echo -echoe -echok -echoctl -echoke`, {
    stdio: "ignore",
  });
  return fs.openSync(
    portPath,
    fs.constants.O_RDWR | fs.constants.O_NONBLOCK | fs.constants.O_NOCTTY
  );
}

/**
 * Close a CDC serial port fd.
 * @param {number} fd
 */
export function closeCdcPort(fd) {
  try {
    fs.closeSync(fd);
  } catch {
    /* ignore */
  }
}

/**
 * Write entire buffer to fd, retrying on partial writes and transient errors.
 * O_NONBLOCK fds can throw EAGAIN when the USB TX buffer is momentarily full.
 * Retries up to 5 times with 1ms spin-waits. Fatal errors (ENXIO) propagate.
 * @param {number} fd
 * @param {Buffer} buf
 */
export function writeCdcPort(fd, buf) {
  let written = 0;
  let retries = 0;
  while (written < buf.length) {
    try {
      const n = fs.writeSync(fd, buf, written, buf.length - written);
      if (n > 0) {
        written += n;
        retries = 0;
      } else {
        retries++;
        if (retries > 5) throw new Error("CDC write: buffer full after 5 retries");
        spinWaitMs(1);
      }
    } catch (err) {
      if (err.code === "EAGAIN" || err.code === "EWOULDBLOCK") {
        retries++;
        if (retries > 5) throw err;
        spinWaitMs(1);
        continue;
      }
      throw err;
    }
  }
}

function spinWaitMs(ms) {
  const target = performance.now() + ms;
  while (performance.now() < target) { /* spin */ }
}

// ---------------------------------------------------------------------------
// Auto-detect CDC port
// ---------------------------------------------------------------------------

/**
 * Scan /dev for cu.usbmodem* devices containing "K1" in the name.
 * ONLY returns K1 CDC data ports. Never touches USB Serial/JTAG debug ports.
 * @returns {string} port path
 * @throws if zero or ambiguous K1 ports found
 */
export function detectCdcPort() {
  const devDir = fs.readdirSync("/dev");
  const k1Ports = devDir.filter((d) => d.startsWith("cu.usbmodem") && /k1/i.test(d));

  if (k1Ports.length === 1) return "/dev/" + k1Ports[0];

  if (k1Ports.length === 0) {
    throw new Error(
      "No K1 CDC port found. Is the device connected and running?"
    );
  }

  const err = new Error(
    `Multiple K1 CDC ports found: ${k1Ports.map((c) => "/dev/" + c).join(", ")}. Specify port explicitly.`
  );
  err.ports = k1Ports.map((c) => "/dev/" + c);
  throw err;
}
