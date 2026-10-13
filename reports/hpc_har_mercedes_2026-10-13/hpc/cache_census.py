import pickle, os, sys, json, collections, csv
class Safe(pickle.Unpickler):
    def find_class(self, m, n):
        raise pickle.UnpicklingError(f"blocked {m}.{n}")
d = sys.argv[1]
c = collections.Counter(); names=[]
files = os.listdir(d)
for f in files:
    with open(os.path.join(d,f),'rb') as fh:
        p = Safe(fh).load()
    a = json.loads(p['name']); c[a[0]] += 1; names.append(a)
print(len(files), dict(c))
