#!/usr/bin/env python3
"""Re-pack the ramdisk of a built boot-v0-v2 image so it matches the STOCK one:
   --comp gzip|lz4|xz|lzma   recompress with the format the stock kernel can unpack
   --mtk NAME                add the 512-byte MediaTek header (e.g. ROOTFS)
Usage: fix_ramdisk.py <image (edited in place)> [--comp X] [--mtk NAME]"""
import argparse, struct, subprocess, sys
MTK = b'\x88\x16\x88\x58'
def align(x, p): return (x + p - 1) // p * p

def comp_of(b):
    if b[:2] == b'\x1f\x8b': return 'gzip'
    if b[:4] in (b'\x02\x21\x4c\x18', b'\x04\x22\x4d\x18'): return 'lz4'
    if b[:6] == b'\xfd7zXZ\x00': return 'xz'
    if b[:3] == b'\x5d\x00\x00': return 'lzma'
    return 'unknown'

DEC = {'gzip': ['gzip', '-dc'], 'lz4': ['lz4', '-dc'], 'xz': ['xz', '-dc'], 'lzma': ['xz', '-dc']}
ENC = {'gzip': ['gzip', '-9n', '-c'], 'lz4': ['lz4', '-l', '-12', '-c'],
       'xz': ['xz', '--check=crc32', '-9e', '-c'], 'lzma': ['xz', '--format=lzma', '-9e', '-c']}

def run(cmd, data):
    p = subprocess.run(cmd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0 or not p.stdout:
        sys.exit('ERROR running %s: %s' % (cmd[0], p.stderr.decode(errors='replace')))
    return p.stdout

ap = argparse.ArgumentParser()
ap.add_argument('image'); ap.add_argument('--comp'); ap.add_argument('--mtk')
ap.add_argument('--stock', help='stock recovery.img: copy its recovery_dtbo, os_version and name')
a = ap.parse_args()
d = bytearray(open(a.image, 'rb').read())
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

body = ramdisk[512:] if ramdisk[:4] == MTK else ramdisk
cur = comp_of(body)
print('built ramdisk: %s%s' % (cur, ' (had MTK header)' if ramdisk[:4] == MTK else ''))
if a.comp and a.comp in ENC and cur != a.comp:
    if cur not in DEC: sys.exit('cannot read current ramdisk compression: ' + cur)
    body = run(ENC[a.comp], run(DEC[cur], body))
    print('recompressed -> %s (%d bytes)' % (a.comp, len(body)))
if a.mtk:
    hdr = (MTK + struct.pack('<I', len(body)) + a.mtk.encode().ljust(32, b'\0')).ljust(512, b'\xff')
    body = hdr + body
    print('added MTK header', a.mtk)
if a.stock:
    sd = open(a.stock, 'rb').read()
    assert sd[:8] == b'ANDROID!', 'stock is not a boot image'
    sver = struct.unpack_from('<I', sd, 40)[0]
    spage = struct.unpack_from('<I', sd, 36)[0]
    sksz, srsz, sssz = struct.unpack_from('<I', sd, 8)[0], struct.unpack_from('<I', sd, 16)[0], struct.unpack_from('<I', sd, 24)[0]
    if sver >= 1 and ver >= 1:
        sdtbo_sz = struct.unpack_from('<I', sd, 1632)[0]
        soff = spage + align(sksz, spage) + align(srsz, spage) + align(sssz, spage)
        dtbo = sd[soff:soff + sdtbo_sz]
        rdtbo = len(dtbo)
        print('copied recovery_dtbo from stock: %d bytes' % rdtbo)
    d[44:48] = sd[44:48]            # os_version / patch level
    d[48:64] = sd[48:64]            # board name
    print('copied os_version %s and name %r from stock' % (sd[44:48].hex(), sd[48:64].split(b"\0")[0]))
struct.pack_into('<I', d, 16, len(body))
if ver >= 1:
    struct.pack_into('<I', d, 1632, rdtbo)
    struct.pack_into('<Q', d, 1636, (page + align(ksz, page) + align(len(body), page) + align(ssz, page)) if rdtbo else 0)
pad = lambda b: b + b'\0' * (-len(b) % page)
out = pad(bytes(d[:page])) + pad(kernel) + pad(body) + pad(second) + pad(dtbo) + pad(dtb) + tail
open(a.image, 'wb').write(out)
print('image rewritten, %d bytes' % len(out))
