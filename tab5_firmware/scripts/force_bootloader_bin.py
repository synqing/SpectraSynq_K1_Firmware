from os.path import join, isfile
from SCons.Script import Import  # type: ignore

Import("env")


def ensure_bootloader_bin():
    platform = env.PioPlatform()
    board = env.BoardConfig()

    mcu = board.get("build.mcu", "esp32p4")
    flash_mode = board.get("build.flash_mode", "qio")
    f_flash = board.get("build.f_flash", "80000000L")
    freq_map = {
        "40000000L": "40m",
        "80000000L": "80m",
        "60000000L": "60m",
    }
    freq = freq_map.get(f_flash, "80m")

    libs_dir = platform.get_package_dir("framework-arduinoespressif32-libs")
    boot_elf = join(libs_dir, mcu, "bin", f"bootloader_{flash_mode}_{freq}.elf")
    out_bin = join(env.subst("$BUILD_DIR"), "bootloader.bin")

    if not isfile(boot_elf):
        print(f"[force_bootloader] Bootloader ELF missing: {boot_elf}")
        return

    # Generate bootloader.bin via esptool elf2image in PlatformIO's env
    cmd = env.Command(
        out_bin,
        boot_elf,
        env.VerboseAction(
            '"$PYTHONEXE" "$OBJCOPY" --chip ' + mcu +
            ' elf2image --flash_mode ${__get_board_flash_mode(__env__)} '
            '--flash_freq ${__get_board_f_image(__env__)} '
            '--flash_size ' + board.get("upload.flash_size", "4MB") + ' -o $TARGET $SOURCES',
            "Building $TARGET",
        ),
    )

    # Make sure firmware depends on bootloader
    env.Depends("$BUILD_DIR/$PROGNAME$PROGSUFFIX", cmd)
    print(f"[force_bootloader] Will build bootloader.bin from: {boot_elf}")


ensure_bootloader_bin()

