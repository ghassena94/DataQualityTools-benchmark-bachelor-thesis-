import warnings; warnings.filterwarnings('ignore')
exec(open('/private/tmp/claude-503/-Users-ghassen-aicha-caronsale-de-Desktop-BA-rein-benchmark/32983ad7-d979-40ea-a9e4-4217ca518e50/scratchpad/gt_flags/bc_experiments.py').read().split("# -- 1. the '?' cells")[0].replace("print(", "(lambda *a, **k: None)("))
def kind(r, c):
    v, t = dirty.iat[r, c], clean.iat[r, c]
    if v == '': return 'blank'
    if c >= 2 and v in [str(i) for i in range(1, 11)] + ['2', '4']: return 'legal value (swap)'
    if not v.isdigit(): return 'not a number'
    return 'other number'
for name in ('dirty_profiled', 'clean_profiled', 'hand_written'):
    found = dets[name] & A
    print(name, 'TP in id cols', sum(1 for x in found if x[1] in (0, 1)), 'TP in attribute cols', sum(1 for x in found if x[1] >= 2))
cp_extra = (dets['clean_profiled'] & A) - (dets['dirty_profiled'] & A)
print('clean_profiled adds', len(cp_extra), 'TPs; by column', pd.Series([cols[c] for _, c in cp_extra]).value_counts().to_dict())
miss = A - dets['hand_written']
print('hand_written misses', len(miss), pd.Series([('id col: ' if c < 2 else '') + kind(r, c) for r, c in miss]).value_counts().to_dict())
allk = pd.Series([('id col: ' if c < 2 else '') + kind(r, c) for r, c in A]).value_counts().to_dict(); print('all errors by kind', allk)
print('UCI columns', pd.read_csv(UCI, header=None).shape[1], 'clean columns', clean.shape[1], 'first clean col values == row number:', (clean['Unnamed: 0'] == clean.index.astype(str)).all())
