import re, struct, zlib, statistics, sys
t = open(sys.argv[1],'rb').read().decode('latin1')
for l in t.splitlines():
    if l.startswith(('BUILD:','[SCAP] ARMED','I2S PDM','[WIREDIAG]')): print(l)
m = re.search(r'\[SCAP-BEGIN len=(\d+) crc32=([0-9a-f]+) frames=(\d+)[^\]]*\]\r?\n(.*?)\[SCAP-END\]', t, re.S)
if not m: print("no dump"); raise SystemExit
hexs = ''.join(x.strip() for x in m.group(4).splitlines() if re.fullmatch(r'[0-9a-f]+', x.strip()))
b = bytes.fromhex(hexs); print("bytes", len(b), "crc_ok", format(zlib.crc32(b),'08x')==m.group(2))
s = struct.unpack('<%dh'%(len(b)//2), b)
for name,x in (('RIGHT(idx0)',s[0::2]),('LEFT(idx1)',s[1::2])):
    print(name,'min',min(x),'max',max(x),'uniq',len(set(x)),'mean',round(statistics.mean(x),1),'pstdev',round(statistics.pstdev(x),1))
