from minigenerator.flowlib.tcp_thomas import sendFlowTCP
import multiprocessing
from random import  uniform
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('sport', type=int, help='sport')
parser.add_argument('dport', type=int, help='dport')
args = parser.parse_args()
sport = args.sport
dport = args.dport

process_list = []

flow_template = {"dst": '10.0.0.2',
                 "dport": dport,
                 "sport": sport,
                 "inter_packet_delay":0.2,
                 "duration":60,
                 "pkt_len":100}

process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
process.daemon = True
process.start()

process_list.append(process)

for p in process_list:
    p.join()
