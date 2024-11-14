import logging 
import subprocess 
import time 
import json 
import sys 
import re 

ALL_METRIC_NAMES = [ 
    "rx_vport_unicast_packets", "rx_vport_unicast_bytes", 
    "tx_vport_unicast_packets", "tx_vport_unicast_bytes", 
    "rx_vport_multicast_packets", "rx_vport_multicast_bytes", 
    "tx_vport_multicast_packets", "tx_vport_multicast_bytes", 
    "rx_vport_broadcast_packets", "rx_vport_broadcast_bytes", 
    "tx_vport_broadcast_packets", "tx_vport_broadcast_bytes", 
    "rx_vport_rdma_unicast_packets", "rx_vport_rdma_unicast_bytes", 
    "tx_vport_rdma_unicast_packets", "tx_vport_rdma_unicast_bytes", 
    "rx_vport_rdma_multicast_packets", "rx_vport_rdma_multicast_bytes", 
    "tx_vport_rdma_multicast_packets", "tx_vport_rdma_multicast_bytes" 
] 

METRIC_NAMES = [ 
    "rx_vport_unicast_bytes", 
    "tx_vport_unicast_bytes", 
    "rx_vport_rdma_unicast_bytes", 
    "tx_vport_rdma_unicast_bytes", 
] 

metrics = {}

def decode_str_list(line_list): 
    return [x.decode("utf-8") for x in line_list]

def get_cmd_out(cmd): 
    return decode_str_list(subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.readlines())


def get_ethtool_stats(interface):
    cmd = ["ethtool", "-S", interface]
    output = get_cmd_out(cmd)
    stats = {}
    for line in output:
        match = re.match(r'\s*(\S+): (\d+)', line)
        if match:
            key = match.group(1)
            value = int(match.group(2))
            stats[key] = value
    return stats

def update_metric():
    global metrics

    time_since_last_update = time.time() - metrics.get("last_update", time.time())
    logging.debug("[update_metrics] Update metrics after %ss", time_since_last_update)

    devices = ["eth0"]
    for device in devices:
        stats = get_ethtool_stats(device)
        metrics[device] = {}

        for metric in METRIC_NAMES:
            if metric in stats:
                if "packets" in metric:
                    num_packets = stats[metric.replace("_vport", "").replace("_", " ")]
                    metrics[device][metric.replace("_vport", "").replace("_", " ")] = num_packets
                elif "bytes" in metric:
                    num_bytes = stats[metric]
                    metrics[device][metric.replace("_vport", "").replace("_", " ")] = num_bytes
                    metrics[device][metric.replace("bytes", "GB/s").replace("_vport", "").replace("_", " ")] = num_bytes / (time_since_last_update * 1024 * 1024 * 1024)

    metrics["last_update"] = time.time()
    
logging.root.setLevel(logging.INFO)
update_interval = 5
is_first_loop = True
while True:
    update_metric()
    if not is_first_loop:
        print("Note: This is a traffic monitor for Infiniband interfaces.")
        print(json.dumps(metrics, indent=2, sort_keys=True))
    else:
        print("Begin, please wait")
    is_first_loop = False
    
    time.sleep(update_interval)
