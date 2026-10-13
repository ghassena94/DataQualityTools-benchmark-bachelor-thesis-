# read-only: extract strategy names from Raha cache pickles WITHOUT unpickling (regex on raw bytes)
import glob, re, sys, collections, os
for folder in sys.argv[1:]:
    files = glob.glob(os.path.join(folder, '*.dictionary'))
    fam = collections.Counter(); names = []; odd = 0
    for f in files:
        b = open(f, 'rb').read(600)
        m = re.search(rb'\["(OD|PVD|RVD|KBVD)", (.*?)\]\]?', b)
        if not m: odd += 1; continue
        fam[m.group(1).decode()] += 1; names.append(m.group(0)[:80].decode('utf-8', 'replace'))
    print(folder, len(files), dict(fam), 'unparsed', odd)
    for n in sorted(x for x in names if x.startswith('["OD') or x.startswith('["RVD'))[:40]: print('   ', n)
