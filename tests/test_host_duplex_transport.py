"""Real bidirectional transport regression; no firmware or device access."""
import subprocess
import sys
import threading
import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS pipe-readiness compatibility")
def test_large_duplex_stream_preserves_every_byte():
    assert subprocess._PIPE_BUF == 1
    data = (b"x" * 80 + b"\n") * 1000
    expected = b"".join(line * 2 for line in data.splitlines(keepends=True))
    code = ("import sys\nfor line in sys.stdin.buffer:\n"
            " sys.stdout.buffer.write(line*2)\n sys.stdout.buffer.flush()\n")
    with subprocess.Popen([sys.executable, "-u", "-c", code],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as child:
        # A blocked write can prevent communicate's own timeout from running.
        # This watchdog kills only this owned infrastructure child on failure.
        watchdog = threading.Timer(15, child.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            out, err = child.communicate(data, timeout=12)
        finally:
            watchdog.cancel()
            if child.poll() is None:
                child.kill()
                child.communicate()
    assert child.returncode == 0, err
    assert out == expected
