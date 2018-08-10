import time
from minigenerator.flowlib.tcp_thomas import recvFlowTCP
import multiprocessing
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('port', type=int, help='port')
args = parser.parse_args()
port = args.port

process_list = []

flow_template = {"dport":port}

process = multiprocessing.Process(target=recvFlowTCP, kwargs=flow_template)
process.daemon = True
process.start()

print 'Receiver started for dport: ', port

process_list.append(process)

time.sleep(100)

for p in process_list:
    p.terminate()
