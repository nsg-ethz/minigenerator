from minigenerator.flowlib.tcp_thomas import sendFlowTCP
import multiprocessing
from random import  uniform
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('exp_nb', type=int, help='Tell which experiment to run')
parser.add_argument('sport', type=int, help='sport')
parser.add_argument('dport', type=int, help='dport')
args = parser.parse_args()
sport = args.sport
dport = args.dport
exp_nb = args.exp_nb

if exp_nb == 1:
    print 'EXP 1'
    process_list = []


    flow_template = {"dst": '192.168.122.166',
                     "dport": dport,
                     "sport": sport,
                     "inter_packet_delay":0.2,
                     "duration":60,
                     "pkt_len":1400}

    process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    process_list.append(process)

    for p in process_list:
        p.join()

elif exp_nb == 2:
    print 'EXP 2'
    process_list = []

    flow_template = {"dst": '192.168.122.166',
                     "dport": dport,
                     "sport": sport,
                     "inter_packet_delay":0.5,
                     "duration":60,
                     "pkt_len":1400}

    process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    process_list.append(process)

    for p in process_list:
        p.join()
