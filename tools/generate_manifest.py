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
                'rows': 8,
                'logcols': lc,
                'thr': 1,
                'frac': 1,
                'hash_units': 8
            }
        ],
        'total_thr': 1
    }
    for lc in range(6, 12, 2)
]

amdahls_cpu_bench = [
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


# mem_bench = [
#     {
#         'sketches': [
#             {
#                 'rows': r,
#                 'cols': 2**logc,
#                 'thr': 1,
#                 'frac': 1
#             }
#         ],
#         'total_thr': 1
#     }
#     for r in [10, 12]
#     for logc in range(23)
# ]

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

yaml.dump(amdahls_cpu_bench, sys.stdout)
