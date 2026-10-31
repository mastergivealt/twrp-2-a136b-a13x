#!/system/bin/sh
# Run as root on the phone:   su -c "sh /sdcard/twrp_probe.sh"
# Collects what the TWRP build needs and backs up your stock recovery/boot/vbmeta.
# Only writes into /sdcard/twrp_probe/.
O=/sdcard/twrp_probe
mkdir -p $O
getprop > $O/getprop.txt
cat /proc/cmdline > $O/cmdline.txt
cat /proc/partitions > $O/partitions.txt
ls -l /dev/block/by-name > $O/by-name.txt 2>&1
cat /proc/mounts > $O/proc_mounts.txt
for f in /vendor/etc/fstab.* /system/etc/recovery.fstab /vendor/etc/recovery.fstab; do
  [ -f "$f" ] && { echo "### $f"; cat "$f"; } >> $O/fstab.txt
done
blockdev --getsize64 /dev/block/by-name/super > $O/super_size.txt 2>&1
uname -a > $O/uname.txt
lsmod > $O/lsmod.txt 2>&1
ls -l /vendor/lib/modules /vendor_dlkm/lib/modules > $O/modules_dir.txt 2>&1
ls /sys/class/backlight > $O/backlight.txt 2>&1
for b in /sys/class/backlight/*; do echo "$b max=$(cat $b/max_brightness 2>/dev/null)"; done >> $O/backlight.txt
getevent -p > $O/getevent.txt 2>&1
df > $O/df.txt 2>&1
for p in recovery boot vbmeta; do
  dd if=/dev/block/by-name/$p of=$O/$p.img bs=1M 2>/dev/null && echo "saved $p.img"
done
cd /sdcard && tar -cf twrp_probe.tar twrp_probe 2>/dev/null
echo "DONE -> /sdcard/twrp_probe/"
