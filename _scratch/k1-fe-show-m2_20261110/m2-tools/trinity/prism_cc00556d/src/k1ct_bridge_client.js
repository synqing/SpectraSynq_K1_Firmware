// K1CT Bridge Client — manages the persistent Python bridge subprocess.
// Sends JSON commands via stdin, receives JSON responses via stdout.
// Serial request queue ensures one K1CT command at a time.

import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BRIDGE_SCRIPT = path.join(__dirname, "..", "tools", "k1ct_bridge.py");

const REQUEST_TIMEOUT_MS = 4000;

export class K1CTBridgeClient {
  #proc = null;
  #rl = null;
  #port = null;
  #queue = [];
  #pending = null; // { resolve, reject, timer }
  #ready = false;
  #readyPromise = null;
  #readyResolve = null;
  #readyReject = null;

  get connected() { return this.#proc !== null && this.#ready; }
  get port() { return this.#port; }

  /**
   * Spawn the bridge subprocess. Resolves when the bridge signals ready.
   * @param {string} portPath - CDC serial port path
   * @returns {Promise<{port: string}>}
   */
  async open(portPath) {
    if (this.#proc) {
      throw new Error("Bridge already open");
    }

    this.#readyPromise = new Promise((resolve, reject) => {
      this.#readyResolve = resolve;
      this.#readyReject = reject;
    });

    this.#proc = spawn("python3", [BRIDGE_SCRIPT, portPath], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    this.#rl = createInterface({ input: this.#proc.stdout });

    this.#rl.on("line", (line) => {
      let parsed;
      try {
        parsed = JSON.parse(line);
      } catch {
        return; // ignore non-JSON output
      }

      // First message is the ready signal.
      if (!this.#ready && parsed.ready) {
        this.#ready = true;
        this.#port = parsed.port;
        this.#readyResolve({ port: parsed.port });
        return;
      }

      // Subsequent messages are responses to queued requests.
      if (this.#pending) {
        clearTimeout(this.#pending.timer);
        this.#pending.resolve(parsed);
        this.#pending = null;
        this.#drainQueue();
      }
    });

    // Capture stderr for diagnostics.
    let stderrBuf = "";
    this.#proc.stderr.on("data", (chunk) => {
      stderrBuf += chunk.toString();
      // Keep only last 2KB.
      if (stderrBuf.length > 2048) stderrBuf = stderrBuf.slice(-2048);
    });

    this.#proc.on("exit", (code) => {
      if (!this.#ready) {
        this.#readyReject(new Error(`Bridge exited before ready (code=${code}): ${stderrBuf.trim()}`));
      }
      this.#cleanup(`Bridge exited (code=${code})`);
    });

    // Timeout: if bridge doesn't signal ready within 5s.
    const readyTimer = setTimeout(() => {
      if (!this.#ready) {
        this.close();
        this.#readyReject(new Error("Bridge ready timeout (5s)"));
      }
    }, 5000);

    const result = await this.#readyPromise;
    clearTimeout(readyTimer);
    return result;
  }

  /**
   * Send a command to the bridge. Returns parsed JSON response.
   * Requests are queued and executed serially.
   * @param {Object} cmd - JSON command object
   * @returns {Promise<Object>}
   */
  request(cmd) {
    if (!this.#proc || !this.#ready) {
      return Promise.reject(new Error("Bridge not connected"));
    }

    return new Promise((resolve, reject) => {
      this.#queue.push({ cmd, resolve, reject });
      if (!this.#pending) {
        this.#drainQueue();
      }
    });
  }

  /**
   * Kill the bridge subprocess.
   */
  close() {
    if (this.#proc) {
      try { this.#proc.stdin.end(); } catch { /* ignore */ }
      try { this.#proc.kill("SIGTERM"); } catch { /* ignore */ }
    }
    this.#cleanup("Bridge closed");
  }

  /**
   * Check if a request is currently in-flight (for polling backpressure).
   */
  get requestPending() {
    return this.#pending !== null;
  }

  // -- Internal --

  #drainQueue() {
    if (this.#pending || this.#queue.length === 0) return;
    if (!this.#proc || !this.#ready) {
      // Reject all queued requests.
      while (this.#queue.length) {
        const { reject } = this.#queue.shift();
        reject(new Error("Bridge not connected"));
      }
      return;
    }

    const { cmd, resolve, reject } = this.#queue.shift();

    const timer = setTimeout(() => {
      if (this.#pending) {
        this.#pending = null;
        reject(new Error(`Bridge request timeout (${REQUEST_TIMEOUT_MS}ms): ${JSON.stringify(cmd)}`));
        this.#drainQueue();
      }
    }, REQUEST_TIMEOUT_MS);

    this.#pending = { resolve, reject, timer };

    try {
      this.#proc.stdin.write(JSON.stringify(cmd) + "\n");
    } catch (err) {
      clearTimeout(timer);
      this.#pending = null;
      reject(new Error(`Bridge write error: ${err.message}`));
      this.#drainQueue();
    }
  }

  #cleanup(reason) {
    // Reject pending request.
    if (this.#pending) {
      clearTimeout(this.#pending.timer);
      this.#pending.reject(new Error(reason));
      this.#pending = null;
    }
    // Reject all queued requests.
    while (this.#queue.length) {
      const { reject } = this.#queue.shift();
      reject(new Error(reason));
    }
    if (this.#rl) {
      this.#rl.close();
      this.#rl = null;
    }
    this.#proc = null;
    this.#ready = false;
    this.#port = null;
  }
}
