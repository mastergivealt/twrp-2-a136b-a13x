#!/usr/bin/env python3
"""Put the 512-byte MediaTek header (magic 0x58881688, size, name) in front of the ramdisk of a boot-v0-v2 image.
Usage: mtk_wrap.py <image in/out> [NAME]   (default NAME=ROOTFS)"""
import struct, sys
MTK = b'\x88\x16\x88\x58'
def align(x, p): return (x + p - 1) // p * p
path = sys.argv[1]; name = (sys.argv[2] if len(sys.argv) > 2 else 'ROOTFS').encode()
d = bytearray(open(path, 'rb').read())
assert d[:8] == b'ANDROID!', 'not a boot image'
ver = struct.unpack_from('<I', d, 40)[0]
assert ver <= 2, 'only header v0-v2 supported'
ksz, kaddr, rsz, raddr, ssz, saddr, taddr, page, _ = struct.unpack_from('<9I', d, 8)
rdtbo = struct.unpack_from('<I', d, 1632)[0] if ver >= 1 else 0
dtbsz = struct.unpack_from('<I', d, 1648)[0] if ver == 2 else 0
off = page
kernel = bytes(d[off:off + ksz]); off += align(ksz, page)
ramdisk = bytes(d[off:off + rsz]); off += align(rsz, page)
second = bytes(d[off:off + ssz]); off += align(ssz, page)
dtbo = bytes(d[off:off + rdtbo]); off += align(rdtbo, page)
dtb = bytes(d[off:off + dtbsz]); off += align(dtbsz, page)
tail = bytes(d[off:])
if ramdisk[:4] == MTK:
    print('ramdisk already has an MTK header, nothing to do'); sys.exit(0)
hdr = MTK + struct.pack('<I', len(ramdisk)) + name.ljust(32, b'\0')
hdr = hdr.ljust(512, b'\xff')
ramdisk = hdr + ramdisk
struct.pack_into('<I', d, 16, len(ramdisk))
pad = lambda b: b + b'\0' * (-len(b) % page)
out = pad(bytes(d[:page])) + pad(kernel) + pad(ramdisk) + pad(second) + pad(dtbo) + pad(dtb) + tail
open(path, 'wb').write(out)
print('wrapped ramdisk with MTK header (%s), new image size %d' % (name.decode(), len(out)))
