"""Show the last N Raha rows of a dataset's detection_results.csv with summary stats."""
import csv, statistics as st, sys
ds = sys.argv[1] if len(sys.argv) > 1 else 'adult'
n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
rows = [r for r in csv.DictReader(open('rein-datasets/%s/results/detection_results.csv' % ds)) if r['detector'] == 'raha'][-n:]
for i, r in enumerate(rows, 1):
    fg = (r['cell_FG1'] or 'undef')[:6]
    print('iter %2d %s  P %.4f R %.4f F1 %.4f FG1 %6s TP %5s FP %5s FN %5s det %6s runtime %8.1f s' % (
        i, r['time'][:16], float(r['precision']), float(r['recall']), float(r['f1']), fg,
        r['cell_TP'], r['cell_FP'], r['cell_FN'], r['#detections'], float(r['detection_runtime'])))
f = [float(r['f1']) for r in rows]
above = sum(1 for r in rows if r['cell_FG1'] and float(r['cell_FG1']) > 0.5)
print('mean %.4f  sd %.4f  min %.4f  max %.4f   FG1 above 0.5: %d/%d' % (st.mean(f), st.stdev(f) if len(f) > 1 else 0, min(f), max(f), above, len(f)))
