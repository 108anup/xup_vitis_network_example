import yaml
import sys
import random
# A proper manifest would have flow filters instead of thr

hash_bench = [
    {
        'sketches': [
            {
                'rows': r,
                'logcols': 6,
                'thr': 1,
                'frac': 1,
                'hash_units': 8
            }
        ],
        'total_thr': 1
    }
    for r in range(1, 13)
]

mem_bench = [
    {
        'sketches': [
            {
                'rows': r,
                'logcols': lc,
                'thr': 1,
                'frac': 1,
                'hash_units': r
            }
        ],
        'total_thr': 1
    }
    for r in [8, 10]
    for lc in range(6, 12, 2)
]

amdahls_hash = [
    {
        'sketches': [
            {
                'rows': 12,
                'logcols': 6,
                'thr': 1,
                'frac': 1,
                'hash_units': h
            }
        ],
        'total_thr': 1
    }
    for h in range(1, 7)
]

gt_list = [(h, r, logc)
           for h in [1, 2, 4]
           for r in [3, 6, 9]
           for logc in [6, 8, 10]]
random.shuffle(gt_list)
sname = 'COUNT_SKETCH'
ground_truth = [
    {
        'sketches': [
            {
                'sketch_name': sname,
                'rows': r,
                'cols': 4**logc,
                'thr': 1,
                'frac': 1,
                'hash_units': h
            }
        ],
        'total_thr': 1
    }
    for (h, r, logc) in gt_list[:6]
]

yaml.dump(amdahls_hash, sys.stdout)


