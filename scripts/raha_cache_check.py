"""Count Raha's cached strategies per family for each dataset and compare with a complete cache."""
import pickle, glob, collections, os, sys
DS = sys.argv[1:] or ['adult', 'smartfactory', 'beers', 'bike', 'breast_cancer', 'nasa', 'soilmoisture']
print('%-44s %6s %5s %10s %6s %6s %6s %6s  %s' % ('dataset / cache folder', 'files', 'cols', 'RVD need', 'RVD', 'PVD', 'OD', 'KBVD', 'verdict'))
import re
for arg in DS:
    if os.path.isdir(arg):  # a moved-aside cache folder given by path
        folder = arg if os.path.basename(arg) == 'strategy-profiling' else os.path.join(arg, 'strategy-profiling')
        ds = re.search(r'raha-baran-results-([a-z_]+)', arg).group(1)
        label = os.path.basename(arg.rstrip('/'))
    else:
        ds = arg
        folder = 'rein-datasets/%s/raha-baran-results-%s/strategy-profiling' % (ds, ds)
        label = ds
    files = glob.glob(folder + '/*.dictionary')
    fam = collections.Counter()
    for f in files:
        try:
            fam[pickle.load(open(f, 'rb'))['name'].split(',')[0].strip("[]'\" ")] += 1
        except Exception:
            pass
    d = len(open('rein-datasets/%s/dirty.csv' % ds).readline().split(','))
    need = d * (d - 1)
    ok = fam['OD'] == 34 and fam['KBVD'] == 1 and fam['RVD'] == need
    print('%-44s %6d %5d %10d %6d %6d %6d %6d  %s' % (label, len(files), d, need, fam['RVD'], fam['PVD'], fam['OD'], fam['KBVD'], 'complete' if ok else 'TRUNCATED' if files else 'no cache'))
