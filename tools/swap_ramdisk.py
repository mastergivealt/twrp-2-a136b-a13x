#!/usr/bin/env python3
"""Bisect helper, runs in seconds on any PC with Python 3.
Takes the STOCK recovery.img as the frame (header, kernel, recovery_dtbo, dtb all untouched) and puts ONLY the
ramdisk of the BUILT TWRP image into it. Recomputes the header id and appends SEANDROIDENFORCE.
  boots TWRP  -> the problem is in the header/params of the built image
  hangs       -> the problem is inside the TWRP ramdisk / init (then check last_kmsg)
Usage: swap_ramdisk.py <stock recovery.img> <built recovery.img> <out recovery.img> [--cmdline-add "text"]
  --cmdline-add appends text to the kernel command line (e.g. androidboot.selinux=permissive)
  --debug-kmsg  adds a tiny service to the TWRP ramdisk that copies /tmp/recovery.log into the kernel log
                (so it shows up in last_kmsg after a failed boot)"""
import gzip, hashlib, struct, sys

def align(x, p): return (x + p - 1) // p * p

def newc_read(raw):
    ents, i = [], 0
    while raw[i:i + 6] == b'070701':
        f = [int(raw[i + 6 + 8 * k:i + 14 + 8 * k], 16) for k in range(13)]
        ino, mode, uid, gid, nlink, mtime, fsz, dmaj, dmin, rmaj, rmin, nsz, chk = f
        name = raw[i + 110:i + 110 + nsz - 1].decode('utf8', 'surrogateescape')
        j = align(i + 110 + nsz, 4)
        data = raw[j:j + fsz]
        i = align(j + fsz, 4)
        if name == 'TRAILER!!!': break
        ents.append(dict(ino=ino, mode=mode, uid=uid, gid=gid, nlink=nlink, mtime=mtime,
                         dmaj=dmaj, dmin=dmin, rmaj=rmaj, rmin=rmin, name=name, data=data))
    return ents

def newc_write(ents):
    out = b''
    for n, e in enumerate(ents + [dict(ino=0, mode=0, uid=0, gid=0, nlink=1, mtime=0, dmaj=0, dmin=0,
                                       rmaj=0, rmin=0, name='TRAILER!!!', data=b'')]):
        nm = e['name'].encode('utf8', 'surrogateescape') + b'\0'
        hdr = b'070701' + b''.join(b'%08x' % v for v in (
            e['ino'], e['mode'], e['uid'], e['gid'], e['nlink'], e['mtime'], len(e['data']),
            e['dmaj'], e['dmin'], e['rmaj'], e['rmin'], len(nm), 0))
        out += hdr + nm
        out += b'\0' * (-len(out) % 4)
        out += e['data']
        out += b'\0' * (-len(out) % 4)
    return out

DBG_SH = b'''#!/system/bin/sh
echo "TWRPDBG: logger up" > /dev/kmsg
n=0
while true; do
  if [ -f /tmp/recovery.log ]; then
    t=$(wc -l < /tmp/recovery.log)
    if [ "$t" -lt "$n" ]; then n=0; echo "TWRPDBG: ---- new log ----" > /dev/kmsg; fi
    if [ "$t" -gt "$n" ]; then
      d=$((t-n)); [ $d -gt 80 ] && d=80
      tail -n +$((n+1)) /tmp/recovery.log | head -n $d | while IFS= read -r l; do echo "TWRPDBG: $l" > /dev/kmsg; done
      n=$((n+d))
    fi
  fi
  sleep 1
done
'''
DBG_RC = b'''
service dbg_kmsg /system/bin/sh /system/bin/dbg_kmsg.sh
    user root
    group root
    seclabel u:r:recovery:s0

on boot
    start dbg_kmsg
'''

def add_debug(ramdisk):
    raw = gzip.decompress(ramdisk)
    ents = newc_read(raw)
    nxt = max([e['ino'] for e in ents] + [0]) + 1
    names = {e['name']: e for e in ents}
    def put(name, data, mode):
        nonlocal nxt
        if name in names:
            names[name]['data'] = data
        else:
            e = dict(ino=nxt, mode=mode, uid=0, gid=0, nlink=1, mtime=0, dmaj=0, dmin=0, rmaj=0, rmin=0, name=name, data=data)
            nxt += 1; ents.append(e); names[name] = e
    put('system/bin/dbg_kmsg.sh', DBG_SH, 0o100755)
    rc = names.get('init.recovery.mt6833.rc')
    put('init.recovery.mt6833.rc', (rc['data'] if rc else b'') + DBG_RC, 0o100644)
    print('debug logger added (init.recovery.mt6833.rc %s)' % ('extended' if rc else 'created'))
    return gzip.compress(newc_write(ents), 9)

def parse(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'ANDROID!', path + ': not a boot image'
    ver = struct.unpack_from('<I', d, 40)[0]
    assert ver == 2, '%s: header v%d, this tool handles v2' % (path, ver)
    ksz, _, rsz, _, ssz, _, _, page, _ = struct.unpack_from('<9I', d, 8)
    rdtbo = struct.unpack_from('<I', d, 1632)[0]
    dtbsz = struct.unpack_from('<I', d, 1648)[0]
    off = page
    s = {}
    s['kernel'] = d[off:off + ksz]; off += align(ksz, page)
    s['ramdisk'] = d[off:off + rsz]; off += align(rsz, page)
    s['second'] = d[off:off + ssz]; off += align(ssz, page)
    s['dtbo'] = d[off:off + rdtbo]; off += align(rdtbo, page)
    s['dtb'] = d[off:off + dtbsz]; off += align(dtbsz, page)
    return d, page, s

args = sys.argv[1:]
extra = ''
debug = '--debug-kmsg' in args
if debug: args.remove('--debug-kmsg')
if '--cmdline-add' in args:
    k = args.index('--cmdline-add'); extra = args[k + 1]; del args[k:k + 2]
sd, page, st = parse(args[0])
bd, bpage, bt = parse(args[1])
hdr = bytearray(sd[:page])
if extra:
    cur = bytes(hdr[64:576]).split(b'\0')[0]
    new = (cur + b' ' + extra.encode()).strip()
    if len(new) > 511: sys.exit('cmdline too long (%d > 511)' % len(new))
    hdr[64:576] = new.ljust(512, b'\0')
    print('cmdline now:', new.decode())
ramdisk = bt['ramdisk']
if debug:
    if ramdisk[:2] != b'\x1f\x8b': sys.exit('built ramdisk is not gzip, cannot patch')
    ramdisk = add_debug(ramdisk)
struct.pack_into('<I', hdr, 16, len(ramdisk))
dtbo_off = page + align(len(st['kernel']), page) + align(len(ramdisk), page) + align(len(st['second']), page)
struct.pack_into('<Q', hdr, 1636, dtbo_off if st['dtbo'] else 0)
sha = hashlib.sha1()
for part in ('kernel', 'ramdisk', 'second', 'dtbo', 'dtb'):
    blob = ramdisk if part == 'ramdisk' else st[part]
    sha.update(blob); sha.update(struct.pack('<I', len(blob)))
hdr[576:608] = (sha.digest() + b'\0' * 12)
pad = lambda b: b + b'\0' * (-len(b) % page)
out = bytes(hdr) + pad(st['kernel']) + pad(ramdisk) + pad(st['second']) + pad(st['dtbo']) + pad(st['dtb'])
out += b'SEANDROIDENFORCE'
open(args[2], 'wb').write(out)
print('stock frame + TWRP ramdisk (%d bytes) -> %s (%d bytes)' % (len(ramdisk), args[2], len(out)))
if len(out) > 41943040: print('WARNING: larger than the 40 MiB recovery partition!')
