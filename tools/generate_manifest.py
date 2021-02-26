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
                'hash_units': 4
            }
        ],
        'total_thr': 1
    }
    for r in range(1, 5)
]

mem_bench = [
    {
        'sketches': [
            {
                'rows': r,
                'logcols': 10,
                'logcols_emem': logce,
                'thr': 1,
                'frac': 1,
                'hash_units': r
            }
        ],
        'total_thr': 1
    }
    for r in [8, 10]
    for logce in range(10, 21, 2)
]

# ground_truth = [
#     {
#         'sketches': [
#             {
#                 'rows': r,
#                 'cols': 4**logc,
#                 'thr': 1,
#                 'frac': 1
#             }
#         ],
#         'total_thr': 1
#     }
#     for r in range(2, 10, 2)
#     for logc in range(2, 12)
# ]

hash_bench_more_hash = [
    {
        'sketches': [
            {
                'rows': r,
                'logcols': 6,
                'thr': 1,
                'frac': 1,
                'hash_units': 4
            }
        ],
        'total_thr': 1
    }
    for r in range(5, 13)
]

gt_list = [(h, r, logce)
           for h in [1, 2, 4]
           for r in [3, 6, 9]
           for logce in [10, 16, 20]]
random.Random(4).shuffle(gt_list)
sname = 'COUNT_SKETCH'
ground_truth = [
    {
        'sketches': [
            {
                'sketch_name': sname,
                'rows': r,
                'logcols': 10,
                'thr': 1,
                'frac': 1,
                'hash_units': h
            }
        ],
        'total_thr': 1
    }
    for (h, r, logce) in gt_list[:6]
]

# Univmon
gt_list = [
    (l, h, r, logce)
    for h in [2, 4]
    for (l, r, logce) in [
            (16, 3, 10),
            (4, 6, 16),
            (8, 9, 20)
    ]
]
sname = 'UNIVMON'
ground_truth_univmon = [
    {
        'sketches': [
            {
                'sketch_name': sname,
                'rows': r,
                'logcols': 6,
                'logcols_emem': logce,
                'thr': 1,
                'frac': 1,
                'hash_units': h,
                'univmon_levels': l
            }
        ],
        'total_thr': 1
    }
    for (l, h, r, logce) in gt_list
]

yaml.dump(hash_bench_more_hash, sys.stdout)
