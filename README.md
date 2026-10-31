# TWRP for Samsung Galaxy A13 5G (SM-A136B, codename a13x) - GitHub Actions build

Status: **untested first draft.** It builds the recovery from *your own stock recovery.img* (kernel, dtb,
boot header and cmdline are read from it, nothing is guessed), but nobody has booted it yet.

## 1. Collect data from your phone (root)
Copy `tools/twrp_probe.sh` to `/sdcard/`, then in a root shell (Termux `su`, or adb shell):

    su -c "sh /sdcard/twrp_probe.sh"

Copy `/sdcard/twrp_probe/` to your PC.

## 2. Put files in the repo
- `stock/recovery.img`  (from the probe; REQUIRED, the build reads kernel/dtb/header from it)
- `stock/vbmeta.img`    (optional, from the probe; the build makes a verification-disabled copy)
- `probe/getprop.txt` and `probe/super_size.txt`  (optional, set codename / platform / super size)
- Commit `by-name.txt`, `fstab.txt`, `lsmod.txt`, `backlight.txt` into `probe/` too, to fix `twrp.flags` later.

## 3. Build
GitHub -> Actions -> "Build TWRP (SM-A136B)" -> Run workflow. ~1.5-3 h. Download artifact `twrp-a136b`:
`TWRP_A136B_AP.tar` = recovery.img (+ patched vbmeta.img).

## 4. Flash (Odin)
Back up first (the probe already saved stock recovery/boot/vbmeta). Download mode -> Odin -> AP = TWRP_A136B_AP.tar,
untick "Auto Reboot". After flashing, force a reboot and immediately hold Vol Up + Power into recovery
(otherwise stock may restore its recovery). Bootloader must stay unlocked.
Rooted with Magisk? If Magisk is installed in the *recovery* partition rather than boot, re-patch afterwards.

## If it does not boot / has no screen or touch
Send me: the failed Actions log, `probe/lsmod.txt`, `probe/modules_dir.txt`. Black screen or dead touch usually means
the display/touch driver is a kernel module that is not inside the recovery ramdisk; that needs the modules copied in.
Decryption (`crypto=true`) is a second step and often needs extra work on Android 14 Samsung firmware.
