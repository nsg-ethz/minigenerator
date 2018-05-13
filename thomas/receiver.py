from minigenerator.flowlib.tcp_thomas import recvFlowTCP
import multiprocessing

process_list = []

for flow_id in range(0, 1000):

    flow_template = {"dport":5000+flow_id}

    process = multiprocessing.Process(target=recvFlowTCP, kwargs=flow_template)
    process.daemon = True
    process.start()

    print 'Receiver started for dport: ', 5000+flow_id

    process_list.append(process)

for p in process_list:
    p.join()
