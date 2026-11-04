"""Re-enumerate the Espressif USB-Serial/JTAG device (VID 0x303A PID 0x1001) via libusb_reset_device."""
import ctypes, sys
lib = ctypes.CDLL('/opt/homebrew/lib/libusb-1.0.0.dylib')
ctx = ctypes.c_void_p()
assert lib.libusb_init(ctypes.byref(ctx)) == 0
lib.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p
h = lib.libusb_open_device_with_vid_pid(ctx, 0x303A, 0x1001)
print("open handle", bool(h))
if h:
    lib.libusb_reset_device.argtypes = [ctypes.c_void_p]
    rc = lib.libusb_reset_device(h)
    print("libusb_reset_device rc", rc)
    lib.libusb_close.argtypes = [ctypes.c_void_p]
    if rc == 0: lib.libusb_close(h)
lib.libusb_exit(ctx)
