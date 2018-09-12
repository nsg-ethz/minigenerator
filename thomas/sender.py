from minigenerator.flowlib.tcp_thomas import sendFlowTCP
import multiprocessing
from random import  uniform

process_list = []

# Create 900 flows with an inter packet delay of 2s
for flow_id in range(100, 1000):

    flow_template = {"dst": '8.0.0.2',
                     "dport": 5000+flow_id,
                     "sport": 6000+flow_id,
                     "inter_packet_delay":uniform(1, 5),
                     "duration": 60}

    print flow_template

    process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    process_list.append(process)

# Create 100 flows with an inter packet delay of 0.2s
for flow_id in range(0, 100):

    flow_template = {"dst": '8.0.0.2',
                     "dport": 5000+flow_id,
                     "sport": 6000+flow_id,
                     "inter_packet_delay":uniform(0.05, 0.4),
                     "duration": 60}

    print flow_template

    process = multiprocessing.Process(target=sendFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    process_list.append(process)

for p in process_list:
    p.join()
