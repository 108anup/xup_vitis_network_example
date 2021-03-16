from vnx_utils import *
import pynq
import numpy as np
import os
import time
from collections import namedtuple
import yaml
import multiprocessing
import subprocess

PROJECT_ROOT = "../"
XCLBINS_DIR = "/home/aliu/xclbins"

# TODO: Take from cli
XCLBINS_DIR = os.path.join(XCLBINS_DIR, "univmon-le")
manifests_file_path = os.path.join(PROJECT_ROOT, "tools/manifests/ground_truth_univmon-emem.yml")
manifests = None
with open(manifests_file_path) as f:
    manifests = yaml.safe_load(f)

if(manifests is None):
    raise Exception("Manifest is None")

xclbin_recv = os.path.join(PROJECT_ROOT, 'benchmark.intf1.xilinx_u280_xdma_201920_3/vnx_benchmark_if1.xclbin')

header = ["sk_name", "levels", "rows", "logcols", "hash_units", "mpps"]
ManifestEntry = namedtuple("ManifestEntry", header)
header_gmem = ["sk_name", "levels", "levels_emem", "rows", "logcols", "logcols_emem", "hash_units", "mpps"]
ManifestEntryGmem = namedtuple("ManifestEntry", header_gmem)


def get_throughput(xclbin, sketch_manifest, entry_list):
    assert(len(pynq.Device.devices) == 2)
    print("Found the following NIC(s)")
    for i in range(len(pynq.Device.devices)):
        print("{}) {}".format(i, pynq.Device.devices[i].name))
    
    workers = pynq.Device.devices
    print("Loading xclbin to sender")
    ol_w0 = pynq.Overlay(xclbin, device=workers[0])
    print("Loading xclbin to reciever")
    # ol_w1 = pynq.Overlay(xclbin_recv, device=workers[1])
    ol_w1 = pynq.Overlay(xclbin, device=workers[1])
    
    print("Link worker 0 {}; link worker 1 {}".format(ol_w0.cmac_1.linkStatus(),ol_w1.cmac_1.linkStatus()))
    
    print("Configuring sender")
    print(ol_w1.networklayer_1.updateIPAddress('192.168.0.10', debug=True))
    #2
    ol_w1.networklayer_1.sockets[1] = ('192.168.0.5', 62177, 60512, True)
    ol_w1.networklayer_1.populateSocketTable()
    #3 
    ol_w1.networklayer_1.arpDiscovery()
    #4
    print(ol_w1.networklayer_1.readARPTable())
    
    print("Configuring reciever")
    print(ol_w0.networklayer_1.getNetworkInfo())
    #2
    ol_w0.networklayer_1.sockets[7] = ('192.168.0.10', 60512, 62177, True)
    ol_w0.networklayer_1.populateSocketTable()
    #3 
    ol_w0.networklayer_1.arpDiscovery()
    #4
    ol_w0.networklayer_1.readARPTable()
    
    print("Configuring recieving application")
    ol_w1_tg = ol_w1.traffic_generator_1_1
    ol_w1_tg.register_map.debug_reset = 1
    ol_w1_tg.register_map.mode = benchmark_mode.index('CONSUMER')
    ol_w1_tg.register_map.CTRL.AP_START = 1
    
    num_packets = 1000_000
    
    # Checking if using gmem
    using_gmem = False
    sketch_buf = None
    sketch_wh = None
    if('logcols_emem' in sketch_manifest):
        using_gmem = True
        print("Setting up memory buffers")
        sketch_kernel = ol_w0.update_sketch_1
        r = int(sketch_manifest['rows'])
        lce = int(sketch_manifest['logcols_emem'])
        ce = (1<<lce)
        size = r * ce
        shape = (r, ce)
        if(sketch_manifest['sketch_name'] == 'UNIVMON'):
            le = int(sketch_manifest['univmon_levels_emem'])
            lc = int(sketch_manifest['logcols'])
            assert(lc == lce)
            size = r * le * ce
            shape = (r, le, ce)
        sketch_buf = pynq.allocate(shape, dtype=np.uint32, target=ol_w0.HBM1)
        sketch_wh = sketch_kernel.start(sketch_buf, num_packets)
    
    print("Configuring sending application")
    freq = 292
    ol_w0_tg = ol_w0.traffic_generator_1_3
    ol_w0_tg.register_map.mode = benchmark_mode.index('PRODUCER')
    ol_w0_tg.register_map.dest_id = 7
    ol_w1_tg.freq = freq
    ol_w0_tg.freq = freq

    print("Starting to send packets")
    for pkt in [num_packets]:
        ol_w0_tg.register_map.debug_reset = 1
        ol_w1_tg.register_map.debug_reset = 1
        ol_w0_tg.register_map.time_between_packets = 0
        ol_w0_tg.register_map.number_packets = pkt
        for i in range(1):
            beats = i + 1
            ol_w0_tg.register_map.number_beats = beats
            ol_w0_tg.register_map.CTRL.AP_START = 1
            while int(ol_w0_tg.register_map.out_traffic_packets) != pkt:
                print("Packets sent till now: ", int(ol_w0_tg.register_map.out_traffic_packets))
                time.sleep(0.8)
            # Get results from local and remote worker
            rx_tot_pkt, rx_thr, rx_time = ol_w1_tg.computeThroughputApp('rx')
            tx_tot_pkt, tx_thr, tx_time = ol_w0_tg.computeThroughputApp('tx')
            # Create dict entry for this particular experiment
            entry_dict = {'size': (beats * 64), 'rx_pkts' : rx_tot_pkt, 'tx_thr': tx_thr, 'rx_thr': rx_thr}
            entry_dict['xclbin'] = xclbin
            entry_list.append(entry_dict)
            throughput = pkt / (rx_time * 1000_000)
            # Reset probes to prepare for next computation
            ol_w0_tg.resetProbes()
            ol_w1_tg.resetProbes() 
            print("Sent {:14,} size: {:4}-Byte done!\tGot {:14,} took {:8.4f} sec, thr: {:.3f} Gbps"\
                  .format(pkt,beats*64, rx_tot_pkt, rx_time, rx_thr))
            time.sleep(0.5)
    
    if(using_gmem):
        del sketch_buf
    
    pynq.Overlay.free(ol_w0)
    pynq.Overlay.free(ol_w1)
    return throughput


prefix = "benchmark.intf1.sketch1_"
suffix = ".xilinx_u280_xdma_201920_3"
binary_file_name = "vnx_benchmark_if1.xclbin"
sketch2tag = {
    'COUNT_MIN_SKETCH': "cm",
    'COUNT_SKETCH': "cs",
    'UNIVMON': "univmon"
}
csvname = {
    'COUNT_MIN_SKETCH': "cm-sketch",
    'COUNT_SKETCH': "count-sketch",
    'UNIVMON': "univmon"
}

entry_list = []
results = []
for manifest in manifests:
    sketch = manifest['sketches'][0]
    sname = 'COUNT_MIN_SKETCH'
    if('sketch_name' in sketch):
        sname = sketch['sketch_name']
    univmon_levels = 16
    if(sname == 'UNIVMON' and 'univmon_levels' in sketch):
        univmon_levels = sketch['univmon_levels']
    r = sketch['rows']
    c = sketch['logcols']
    h = sketch['hash_units']

    lce = None
    lce_tag = ""
    if('logcols_emem' in sketch):
        lce = sketch['logcols_emem']
        lce_tag = "_e{}".format(lce)

    le = 16
    tag = "{}_r{}_c{}{}_h{}".format(sketch2tag[sname], r, c, lce_tag, h)
    if(sname == 'UNIVMON'):
        if('logcols_emem' in sketch):
            le = sketch['univmon_levels_emem']
            le_tag = "_le{}".format(le)
        tag = "{}_l{}{}_r{}_c{}{}_h{}".format(sketch2tag[sname], 
                                              univmon_levels, le_tag,
                                              r, c, lce_tag, h)

    binary_file_dir = prefix + tag + suffix
    binary_file_path = os.path.join(
        XCLBINS_DIR, os.path.join(binary_file_dir, binary_file_name))
    print(binary_file_path)
    if(os.path.isfile(binary_file_path)):
        pool = multiprocessing.Pool(processes=1)
        out = pool.starmap(get_throughput, [(binary_file_path, sketch, entry_list)])
        # thr = get_throughput(binary_file_path, sketch)
        thr = out[0]
        if(lce is None):
            results.append(ManifestEntry(csvname[sname], univmon_levels, r, c, h, thr))
        else:
            results.append(ManifestEntryGmem(csvname[sname], univmon_levels, le, r, c, lce, h, thr))
            header = header_gmem
        pool.terminate()
        with open('xbutil_stdin.txt', 'r') as f:
            subprocess.run("xbutil reset", shell=True, stdin=f)


# TODO: Update this script:
print("")
print(", ".join(header))
for entry in results:
    for hdr in header:
        print("{}, ".format(getattr(entry, hdr)), end="")
    print()
