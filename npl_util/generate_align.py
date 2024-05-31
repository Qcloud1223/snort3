# !/usr/bin/python3

# generate aligned HTTP request

# from scapy.all import *
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.utils import PcapWriter
import sys
import copy
import random
from tqdm import tqdm

syn_data = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x00<\xa5\x16@\x00@\x06\x0d\x8c\xc0\xa8\x03d\xc0\xa8\x03e\xa96\x00P\x01\xc2m\xe5\x00\x00\x00\x00\xa0\x02\xfa\xf0\x88H\x00\x00\x02\x04\x05\xb4\x04\x02\x08\x0a\xcc\xf0bt\x00\x00\x00\x00\x01\x03\x03\x07"
syn_ack_data = b"\x00\x1b!\xbb\xf28\x90\xe2\xba\x8a\xfe\x08\x08\x00E\x00\x00<\x00\x00@\x00@\x06\xb2\xa2\xc0\xa8\x03e\xc0\xa8\x03d\x00P\xa96\xb3CN\xed\x01\xc2m\xe6\xa0\x12\xfe\x88\x8b\xe3\x00\x00\x02\x04\x05\xb4\x04\x02\x08\x0a\xd9_\x11E\xcc\xf0bt\x01\x03\x03\x07"
ack_data = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x004\xa5\x17@\x00@\x06\x0d\x93\xc0\xa8\x03d\xc0\xa8\x03e\xa96\x00P\x01\xc2m\xe6\xb3CN\xee\x80\x10\x01\xf6\x88@\x00\x00\x01\x01\x08\x0a\xcc\xf0bt\xd9_\x11E"

http_request = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x00e\xa5\x18@\x00@\x06\x0da\xc0\xa8\x03d\xc0\xa8\x03e\xa96\x00P\x01\xc2m\xe6\xb3CN\xee\x80\x18\x01\xf6\x88q\x00\x00\x01\x01\x08\x0a\xcc\xf0bt\xd9_\x11EGET /index.html HTTP/1.1\x0d\x0aHost: 192.168.3.101\x0d\x0a\x0d\x0a"
# not used in further requests
# request_ack = b"\x00\x1b!\xbb\xf28\x90\xe2\xba\x8a\xfe\x08\x08\x00E\x00\x004\x90L@\x00@\x06\"^\xc0\xa8\x03e\xc0\xa8\x03d\x00P\xa96\xb3CN\xee\x01\xc2n\x17\x80\x10\x01\xfd\xb7\x0a\x00\x00\x01\x01\x08\x0a\xd9_\x11E\xcc\xf0bt"
server_response1 = b"\x00\x1b!\xbb\xf28\x90\xe2\xba\x8a\xfe\x08\x08\x00E\x00\x01\"\x90M@\x00@\x06!o\xc0\xa8\x03e\xc0\xa8\x03d\x00P\xa96\xb3CN\xee\x01\xc2n\x17\x80\x18\x01\xfd>d\x00\x00\x01\x01\x08\x0a\xd9_\x11E\xcc\xf0btHTTP/1.1 200 OK\x0d\x0aServer: nginx/1.26.0\x0d\x0aDate: Thu, 30 May 2024 13:29:00 GMT\x0d\x0aContent-Type: text/html\x0d\x0aContent-Length: 615\x0d\x0aLast-Modified: Sat, 11 May 2024 13:43:14 GMT\x0d\x0aConnection: keep-alive\x0d\x0aETag: \"663f75f2-267\"\x0d\x0aAccept-Ranges: bytes\x0d\x0a\x0d\x0a"
# not used in further requests
# response1_ack = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x004\xa5\x19@\x00@\x06\x0d\x91\xc0\xa8\x03d\xc0\xa8\x03e\xa96\x00P\x01\xc2n\x17\xb3CO\xdc\x80\x10\x01\xf5\x88@\x00\x00\x01\x01\x08\x0a\xcc\xf0bt\xd9_\x11E"
server_response2 = b"\x00\x1b!\xbb\xf28\x90\xe2\xba\x8a\xfe\x08\x08\x00E\x00\x02\x9b\x90N@\x00@\x06\x1f\xf5\xc0\xa8\x03e\xc0\xa8\x03d\x00P\xa96\xb3CO\xdc\x01\xc2n\x17\x80\x18\x01\xfd\x1f)\x00\x00\x01\x01\x08\x0a\xd9_\x11E\xcc\xf0bt<!DOCTYPE html>\x0a<html>\x0a<head>\x0a<title>Welcome to nginx!</title>\x0a<style>\x0ahtml { color-scheme: light dark; }\x0abody { width: 35em; margin: 0 auto;\x0afont-family: Tahoma, Verdana, Arial, sans-serif; }\x0a</style>\x0a</head>\x0a<body>\x0a<h1>Welcome to nginx!</h1>\x0a<p>If you see this page, the nginx web server is successfully installed and\x0aworking. Further configuration is required.</p>\x0a\x0a<p>For online documentation and support please refer to\x0a<a href=\"http://nginx.org/\">nginx.org</a>.<br/>\x0aCommercial support is available at\x0a<a href=\"http://nginx.com/\">nginx.com</a>.</p>\x0a\x0a<p><em>Thank you for using nginx.</em></p>\x0a</body>\x0a</html>\x0a"
response2_ack = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x004\xa5\x1a@\x00@\x06\x0d\x90\xc0\xa8\x03d\xc0\xa8\x03e\xa96\x00P\x01\xc2n\x17\xb3CRC\x80\x10\x01\xf1\x88@\x00\x00\x01\x01\x08\x0a\xcc\xf0bt\xd9_\x11E"

# NOTE: wrong syn, ack and timestamp
fin1 = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x004\x83,@\x00@\x06/~\xc0\xa8\x03d\xc0\xa8\x03e\xb0\x18\x00P$j\x15a\xbf\xfe7\x89\x80\x11\x01\xf5\x88@\x00\x00\x01\x01\x08\x0a\xcc\x9c\x87c\xd9\x0b5\xdd"
fin2 = b"\x00\x1b!\xbb\xf28\x90\xe2\xba\x8a\xfe\x08\x08\x00E\x00\x004MO@\x00@\x06e[\xc0\xa8\x03e\xc0\xa8\x03d\x00P\xb0\x18\xbf\xfe7\x89$j\x15b\x80\x11\x01\xfd\xa7\xf2\x00\x00\x01\x01\x08\x0a\xd9\x0b5\xea\xcc\x9c\x87c"
fin3 = b"\x90\xe2\xba\x8a\xfe\x08\x00\x1b!\xbb\xf28\x08\x00E\x00\x004\x83-@\x00@\x06/}\xc0\xa8\x03d\xc0\xa8\x03e\xb0\x18\x00P$j\x15b\xbf\xfe7\x8a\x80\x10\x01\xf5\x88@\x00\x00\x01\x01\x08\x0a\xcc\x9c\x87c\xd9\x0b5\xea"

syn_pkt = Ether(syn_data)
syn_ack_pkt = Ether(syn_ack_data)
ack_pkt = Ether(ack_data)
request_pkt = Ether(http_request)
response1_pkt = Ether(server_response1)
response2_pkt = Ether(server_response2)
response_ack_pkt = Ether(response2_ack)
fin1_pkt = Ether(fin1)
fin2_pkt = Ether(fin2)
fin3_pkt = Ether(fin3)

def set_ports(src_port):
    syn_pkt[TCP].sport = src_port
    syn_ack_pkt[TCP].dport = src_port
    ack_pkt[TCP].sport = src_port
    request_pkt[TCP].sport = src_port
    response1_pkt[TCP].dport = src_port
    response2_pkt[TCP].dport = src_port
    response_ack_pkt[TCP].sport = src_port
    fin1_pkt[TCP].sport = src_port
    fin2_pkt[TCP].dport = src_port
    fin3_pkt[TCP].sport = src_port

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("usage: python generate_align.py single_flow_requests flows")
        exit(1)

    out_path_seq = f"/home/iom/snort3-git/test_trace/align_f{int(sys.argv[1])}_r{int(sys.argv[2])}.pcap"
    out_path_sort = f"/home/iom/snort3-git/test_trace/align_f{int(sys.argv[1])}_r{int(sys.argv[2])}_sorted.pcap"
    writer_seq = PcapWriter(out_path_seq)
    writer_sort = PcapWriter(out_path_sort)

    base_port = random.randint(10000, 65535)
    all_flows = []

    for flow_idx in tqdm(range(int(sys.argv[2])), desc="Packet Generation"):
        seq = ack_pkt[TCP].seq
        ack = ack_pkt[TCP].ack
        options = ack_pkt[TCP].options
        for o in options:
            if o[0] == 'Timestamp':
                ts_client = o[1][0]
                ts_server = o[1][1]
        
        set_ports(base_port + flow_idx)
        
        flow_pkts = []
        flow_pkts.append(copy.deepcopy(syn_pkt))
        flow_pkts.append(copy.deepcopy(syn_ack_pkt))
        flow_pkts.append(copy.deepcopy(ack_pkt))

        for i in range(int(sys.argv[1])):
            ts_client += 1
            request_pkt[TCP].seq = seq
            request_pkt[TCP].ack = ack
            # keep all but timestamp
            options = [tp for tp in request_pkt[TCP].options if tp[0] != 'Timestamp']
            options.append(('Timestamp', (ts_client, ts_server)))
            request_pkt[TCP].options = options
            flow_pkts.append(copy.deepcopy(request_pkt))
            seq += len(request_pkt[TCP].payload)
            
            ts_server += 1
            response1_pkt[TCP].seq = ack
            response1_pkt[TCP].ack = seq
            options = [tp for tp in response1_pkt[TCP].options if tp[0] != 'Timestamp']
            options.append(('Timestamp', (ts_server, ts_client)))
            response1_pkt[TCP].options = options
            flow_pkts.append(copy.deepcopy(response1_pkt))
            ack += len(response1_pkt[TCP].payload)

            response2_pkt[TCP].seq = ack
            response2_pkt[TCP].ack = seq
            options = [tp for tp in response2_pkt[TCP].options if tp[0] != 'Timestamp']
            options.append(('Timestamp', (ts_server, ts_client)))
            response2_pkt[TCP].options = options
            flow_pkts.append(copy.deepcopy(response2_pkt))
            ack += len(response2_pkt[TCP].payload)

            ts_client += 1
            response_ack_pkt[TCP].seq = seq
            response_ack_pkt[TCP].ack = ack
            options = [tp for tp in response_ack_pkt[TCP].options if tp[0] != 'Timestamp']
            options.append(('Timestamp', (ts_client, ts_server)))
            response_ack_pkt[TCP].options = options
            flow_pkts.append(copy.deepcopy(response_ack_pkt))
            seq += len(response_ack_pkt[TCP].payload)
        
        # client-oriented FIN
        ts_client += 1
        fin1_pkt[TCP].seq = seq
        fin1_pkt[TCP].ack = ack
        options = [tp for tp in fin1_pkt[TCP].options if tp[0] != 'Timestamp']
        options.append(('Timestamp', (ts_client, ts_server)))
        fin1_pkt[TCP].options = options
        flow_pkts.append(copy.deepcopy(fin1_pkt))
        seq += 1
        
        ts_server += 1
        fin2_pkt[TCP].seq = ack
        fin2_pkt[TCP].ack = seq
        options = [tp for tp in fin2_pkt[TCP].options if tp[0] != 'Timestamp']
        options.append(('Timestamp', (ts_server, ts_client)))
        fin2_pkt[TCP].options = options
        flow_pkts.append(copy.deepcopy(fin2_pkt))
        ack += 1

        ts_client += 1
        fin3_pkt[TCP].seq = seq
        fin3_pkt[TCP].ack = ack
        options = [tp for tp in fin3_pkt[TCP].options if tp[0] != 'Timestamp']
        options.append(('Timestamp', (ts_client, ts_server)))
        fin3_pkt[TCP].options = options
        flow_pkts.append(copy.deepcopy(fin3_pkt))

        # flow is finished
        all_flows.append(flow_pkts)

    # output sequential trace
    for f in tqdm(all_flows, desc="Sequential Trace Export"):
        for p in f:
            writer_seq.write(p)
    
    flow_len = len(all_flows[0])
    for i in tqdm(range(flow_len), desc="Ordered Trace Export"):
        for f in all_flows:
            writer_sort.write(f[i])