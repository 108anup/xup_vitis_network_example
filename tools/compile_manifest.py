import yaml
import sys
import subprocess
import os
from pathlib import Path
from multiprocessing.pool import ThreadPool

PROJECT_DIR = "../"
STATUS_DIR = "build_status"
PARALLELISM = 3


def compile_manifest_util(manifest):
    # Currently only implementing one sketch at a time
    sketch = manifest['sketches'][0]
    sketch_name = 'COUNT_MIN_SKETCH'
    if('sketch_name' in sketch):
        sketch_name = sketch['sketch_name']

    univmon_levels = 8
    univmon_levels_emem = 8
    if(sketch_name == 'UNIVMON' and 'univmon_levels' in sketch):
        univmon_levels = sketch['univmon_levels']
        univmon_levels_emem = sketch['univmon_levels_emem']

    rows = sketch['rows']
    logcols = sketch['logcols']
    logcols_emem = sketch['logcols_emem']
    hash_units = sketch['hash_units']
    # https://www.saltycrane.com/blog/2011/04/how-use-bash-shell-python-subprocess-instead-binsh/
    cmd = ["make", "all", "DEVICE=xilinx_u280_xdma_201920_3",
           "INTERFACE=1", "DESIGN=benchmark", "SKETCH=1",
           "CM_ROWS={}".format(rows),
           "CM_COLS={}".format(logcols),
           "CM_COLS_EMEM={}".format(logcols_emem),
           "HASH_UNITS={}".format(hash_units),
           "SKETCH_NAME={}".format(sketch_name),
           "UNIVMON_LEVELS={}".format(univmon_levels),
           "UNIVMON_LEVELS_EMEM={}".format(univmon_levels_emem)
           ]
    cmd_string = " ".join(cmd)

    # Just for testing if working properly
    # cmd_string = "echo \"{}\"; sleep 10".format(cmd_string)

    tag = "{}-r{}-c{}-e{}-h{}".format(sketch_name, rows,
                                      logcols, logcols_emem, hash_units)
    if(sketch_name == 'UNIVMON'):
        tag = "{}-l{}-le{}-r{}-c{}-e{}-h{}".format(
            sketch_name, univmon_levels, univmon_levels_emem, rows,
            logcols, logcols_emem, hash_units)

    print("Running: {}".format(cmd))
    fout = open(os.path.join(STATUS_DIR, "{}.stdout".format(tag)), "w")
    ferr = open(os.path.join(STATUS_DIR, "{}.stderr".format(tag)), "w")
    # https://stackoverflow.com/questions/4856583/how-do-i-pipe-a-subprocess-call-to-a-text-file
    p = subprocess.Popen(cmd_string, shell=True, stdout=fout, stderr=ferr)
    p.wait()
    fout.close()
    ferr.close()


manifests_file = sys.argv[1]
with open(manifests_file) as f:
    manifests = yaml.safe_load(f)

os.chdir(PROJECT_DIR)
# https://stackoverflow.com/questions/273192/how-can-i-safely-create-a-nested-directory
Path(STATUS_DIR).mkdir(parents=True, exist_ok=True)

# https://stackoverflow.com/questions/26774781/python-multiple-subprocess-with-a-pool-queue-recover-output-as-soon-as-one-finis
tp = ThreadPool(PARALLELISM)

print("Total manifests:", len(manifests))
for manifest in manifests:
    # compile_manifest_util(manifest)
    tp.apply_async(compile_manifest_util, (manifest,))

# https://stackoverflow.com/questions/35708371/purpose-of-pool-join-pool-close-in-multiprocessing
tp.close()
tp.join()
