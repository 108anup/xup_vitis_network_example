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
XCLBINS_DIR = os.path.join(XCLBINS_DIR, "count-sketch-emem")
manifests_file_path = os.path.join(PROJECT_ROOT, "tools/manifests/ground_truth_count-sketch-emem.yml")
manifests = None
with open(manifests_file_path) as f:
    manifests = yaml.safe_load(f)

if(manifests is None):
    raise Exception("Manifest is None")

xclbin_recv = os.path.join(PROJECT_ROOT, 'benchmark.intf1.xilinx_u280_xdma_201920_3/vnx_benchmark_if1.xclbin')

header = ["sketch_name", "r", "c", "h", "thr"]
ManifestEntry = namedtuple("ManifestEntry", header)
header_gmem = ["sketch_name", "r", "c", "e", "h", "thr"]
ManifestEntryGmem = namedtuple("ManifestEntry", header_gmem)

entry_list = []

def get_throughput(xclbin, sketch_manifest):
    assert(len(pynq.Device.devices) == 2)
    print("Found the following NIC(s)")
    for i in range(len(pynq.Device.devices)):
        print("{}) {}".format(i, pynq.Device.devices[i].name))
    
    workers = pynq.Device.devices
    print("Loading xclbin to sender")
    ol_w0 = pynq.Overlay(xclbin, device=workers[0])
    print("Loading xclbin to reciever")
    ol_w1 = pynq.Overlay(xclbin_recv, device=workers[1])
    
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
    
    num_packets = 10000
    
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
            try:
                rx_tot_pkt, rx_thr, rx_time = ol_w1_tg.computeThroughputApp('rx')
            except:
                pass
            try:
                tx_tot_pkt, tx_thr, tx_time = ol_w0_tg.computeThroughputApp('tx')
            except:
                pass
            # Create dict entry for this particular experiment
            try:
                entry_dict = {'size': (beats * 64), 'rx_pkts' : rx_tot_pkt, 'tx_thr': tx_thr, 'rx_thr': rx_thr}
                entry_dict['xclbin'] = xclbin
                entry_list.append(entry_dict)
            except:
                pass
            try:
                throughput = pkt / (rx_time * num_packets)
            except:
                throughput = pkt / (tx_time * num_packets)
            # Reset probes to prepare for next computation
            ol_w0_tg.resetProbes()
            ol_w1_tg.resetProbes() 
            try:
                print("Sent {:14,} size: {:4}-Byte done!\tGot {:14,} took {:8.4f} sec, thr: {:.3f} Gbps"\
                      .format(pkt,beats*64, rx_tot_pkt, rx_time, rx_thr))
            except:
                pass
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

    tag = "{}_r{}_c{}{}_h{}".format(sketch2tag[sname], r, c, lce_tag, h)
    if(sname == 'UNIVMON'):
        tag = "{}_l{}_r{}_c{}{}_h{}".format(sketch2tag[sname], univmon_levels, 
                                            r, c, lce_tag, h)

    binary_file_dir = prefix + tag + suffix
    binary_file_path = os.path.join(
        XCLBINS_DIR, os.path.join(binary_file_dir, binary_file_name))
    print(binary_file_path)
    if(os.path.isfile(binary_file_path)):
        pool = multiprocessing.Pool(processes=1)
        out = pool.starmap(get_throughput, [(binary_file_path, sketch)])
        # thr = get_throughput(binary_file_path, sketch)
        thr = out[0]
        if(lce is None):
            results.append(ManifestEntry("cm-sketch", r, c, h, thr))
        else:
            results.append(ManifestEntryGmem("cm-sketch", r, c, lce, h, thr))
        pool.terminate()
        with open('xbutil_stdin.txt', 'r') as f:
            subprocess.run("xbutil reset", shell=True, stdin=f)


# TODO: Update this script:
for entry in results:
    for hdr in header:
        print("{}, ".format(getattr(entry, hdr)), end="")
    print()
