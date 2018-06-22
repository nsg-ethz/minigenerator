from minigenerator.flowlib.tcp_thomas import sendFlowTCP
import multiprocessing
from random import  uniform

process_list = []

for flow_id in range(0, 1):

    flow_template = {"dst": '8.0.0.2',
                     "dport": 5500+flow_id,
                     "sport": 6000+flow_id,
                     "inter_packet_delay":0.5,
                     "duration":60,
                     "pkt_len":5}

    process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    process_list.append(process)

for p in process_list:
    p.join()
