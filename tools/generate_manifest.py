import yaml
import sys
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
                'logcols': 12,
                'logcols_emem': logce,
                'thr': 1,
                'frac': 1,
                'hash_units': r
            }
        ],
        'total_thr': 1
    }
    for r in [10]
    for logce in range(12, 23, 2)
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

yaml.dump(mem_bench, sys.stdout)
