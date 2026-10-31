#!/usr/bin/env python3
"""Set the AVB 'disable verity + disable verification' flags (=3) in a vbmeta.img."""
import struct, sys
src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
if d[:4] != b'AVB0': sys.exit('not a vbmeta image')
struct.pack_into('>I', d, 120, 3)
open(dst, 'wb').write(d)
print('patched flags -> 3:', dst)
