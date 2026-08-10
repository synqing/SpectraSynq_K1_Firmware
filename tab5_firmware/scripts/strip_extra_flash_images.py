from os.path import join, isfile
from SCons.Script import Import  # type: ignore

Import("env")


def sanitize_flash_images():
    """
    Replace PlatformIO's FLASH_EXTRA_IMAGES with a safe, minimal set.

    ESP-IDF generates the ESP32-P4 bootloader at BUILD_DIR/bootloader.bin while
    PlatformIO may point at BUILD_DIR/bootloader/bootloader.bin. Keep the
    generated bootloader in the upload set at the offset declared by
    flasher_args.json.
    """
    build_dir = env.subst("$BUILD_DIR")

    partitions_path = join(build_dir, "partitions.bin")
    bootloader_path = join(build_dir, "bootloader.bin")
    framework_dir = env.PioPlatform().get_package_dir("framework-arduinoespressif32")
    boot_app0_path = join(
        framework_dir or "",
        "tools",
        "partitions",
        "boot_app0.bin",
    )

    images = []
    if isfile(bootloader_path):
        images.append(("0x2000", bootloader_path))
    if isfile(partitions_path):
        images.append(("0x8000", partitions_path))
    if isfile(boot_app0_path):
        # OTA data initial image (Arduino)
        images.append(("0xe000", boot_app0_path))

    env.Replace(FLASH_EXTRA_IMAGES=images)
    print(f"[strip_extra_flash_images] FLASH_EXTRA_IMAGES -> {images}")


sanitize_flash_images()
