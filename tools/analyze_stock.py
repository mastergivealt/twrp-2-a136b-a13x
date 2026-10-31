#!/usr/bin/env python3
"""Print a diagnostic report about the STOCK recovery.img: header, MTK wrappers, ramdisk
compression + file list, and (if embedded) the kernel config bits that matter for TWRP."""
import re, struct, subprocess, sys, zlib

def align(x, p): return (x + p - 1) // p * p
MTK = b'\x88\x16\x88\x58'

def comp_of(b):
    if b[:2] == b'\x1f\x8b': return 'gzip'
    if b[:4] in (b'\x02\x21\x4c\x18', b'\x04\x22\x4d\x18'): return 'lz4'
    if b[:6] == b'\xfd7zXZ\x00': return 'xz'
    if b[:3] == b'\x5d\x00\x00': return 'lzma'
    if b[:3] == b'BZh': return 'bzip2'
    if b[:6] in (b'070701', b'070707', b'070702'): return 'raw-cpio'
    return 'unknown'

def decompress(b, comp):
    cmd = {'gzip': ['gzip', '-dc'], 'lz4': ['lz4', '-dc'], 'xz': ['xz', '-dc'],
           'lzma': ['xz', '-dc'], 'bzip2': ['bzip2', '-dc']}.get(comp)
    if comp == 'raw-cpio': return b
    if not cmd: return None
    p = subprocess.run(cmd, input=b, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout if p.stdout else None

def newc_names(raw):
    """Minimal 'newc' cpio lister (no external cpio needed)."""
    names, i = [], 0
    while raw[i:i + 6] in (b'070701', b'070702'):
        f = raw[i + 6:i + 110]
        filesize = int(f[48:56], 16); namesize = int(f[88:96], 16)
        name = raw[i + 110:i + 110 + namesize - 1].decode('utf8', 'replace')
        if name == 'TRAILER!!!': break
        names.append(name)
        i = align(i + 110 + namesize, 4)
        i = align(i + filesize, 4)
    return names

def ikconfig(kernel):
    data = kernel[512:] if kernel[:4] == MTK else kernel
    blobs = [data]
    if data[:2] == b'\x1f\x8b':
        try: blobs.append(zlib.decompressobj(31).decompress(data))
        except Exception: pass
    for blob in blobs:
        i = blob.find(b'IKCFG_ST')
        if i >= 0:
            try: return zlib.decompressobj(31).decompress(blob[i + 8:]).decode('ascii', 'replace')
            except Exception: pass
    return None

d = open(sys.argv[1], 'rb').read()
print('== stock image:', sys.argv[1], len(d), 'bytes')
assert d[:8] == b'ANDROID!', 'not an Android boot image'
ver = struct.unpack_from('<I', d, 40)[0]
(ksz, kaddr, rsz, raddr, ssz, saddr, taddr, page, _) = struct.unpack_from('<9I', d, 8)
rdtbo = struct.unpack_from('<I', d, 1632)[0] if ver >= 1 else 0
dtbsz = struct.unpack_from('<I', d, 1648)[0] if ver == 2 else 0
osv = struct.unpack_from('<I', d, 44)[0]
print('header v%d page=%d kernel=%d@0x%x ramdisk=%d@0x%x second=%d tags@0x%x dtbo=%d dtb=%d'
      % (ver, page, ksz, kaddr, rsz, raddr, ssz, taddr, rdtbo, dtbsz))
print('os_version raw 0x%08x' % osv)
print('name:', d[48:64].split(b'\0')[0], '| cmdline:', (d[64:576].split(b'\0')[0] + d[608:1632].split(b'\0')[0]).decode('ascii', 'replace'))
off = page
kernel = d[off:off + ksz]; off += align(ksz, page)
ramdisk = d[off:off + rsz]; off += align(rsz, page)
off += align(ssz, page) + align(rdtbo, page) + align(dtbsz, page)
tail = d[off:]
print('trailing bytes after image:', len(tail), tail[:32])
print('kernel head:', kernel[:16].hex(), 'mtk-wrapped:', kernel[:4] == MTK,
      '| kernel format:', comp_of(kernel[512:] if kernel[:4] == MTK else kernel))
print('ramdisk head:', ramdisk[:16].hex(), 'mtk-wrapped:', ramdisk[:4] == MTK,
      ramdisk[8:40].split(b'\0')[0] if ramdisk[:4] == MTK else '')
rd = ramdisk[512:] if ramdisk[:4] == MTK else ramdisk
comp = comp_of(rd)
print('ramdisk compression:', comp)
raw = decompress(rd, comp)
if raw:
    print('ramdisk unpacked: %d bytes' % len(raw))
    names = newc_names(raw)
    print('ramdisk entries:', len(names))
    for n in names:
        if re.search(r'(^init|recovery|fstab|sepolicy|selinux|\.rc$|modules|\.ko$|vendor_boot|lib/modules)', n) and n.count('/') < 5:
            print('  ', n)
cfg = ikconfig(kernel)
if cfg:
    print('== kernel config (embedded)')
    for line in cfg.splitlines():
        if re.match(r'(# )?CONFIG_(RD_|SECURITY_SELINUX|MODULES\b|MODULE_SIG|BLK_DEV_INITRD|DRM_MEDIATEK|MTK_FB|FB_MTK|SEC_|KNOX|UH\b|RKP|DEFEX|PROCA)', line):
            print(line)
else:
    print('== no embedded kernel config found (IKCONFIG not built in)')
