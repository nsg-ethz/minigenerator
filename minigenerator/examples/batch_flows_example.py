"""
Example of how to send single flow commands to flow servers



"""
from minigenerator.misc.unixsockets import UnixClientTCP
from minigenerator.misc.topology import Topology
from minigenerator import tcp_server_address, topology_path
import random, time

#load topology
topo = Topology(db=topology_path)

#create unix socket client with flow server address (udp)
client = UnixClientTCP(tcp_server_address)

#get hosts
hosts = topo.getHosts().keys()

starting_port = 5000

flow_list = []
number_of_flows = 200
max_size = 20000000 #10Mbit or 1.25Mbytes
max_starting_time = 50

#compute some random flows
for i in xrange(number_of_flows):

    src = random.choice(hosts)
    dst = random.choice(hosts)
    #until they are different
    while src == dst:
        dst = random.choice(hosts)

    #randoms size between 1Kbytes and maxsize
    random_size = random.randint(8000, max_size)

    send_rate = topo.interface_bandwidth(src,"{0}-eth0".format(src))
    #convert it to MBIT/s
    send_rate = "%dM" % send_rate

    flow_template = {"src": src,
                     "dst": dst,
                     "dport": starting_port+i,
                     "sport": starting_port+i,
                     "proto": "TCP",
                     "duration": 0,
                     "size": random_size,
                     "rate": send_rate,
                     "start_time": random.randint(0,max_starting_time)}

    flow_list.append(flow_template)

#separate them per source and send to servers so they schedule them
flows_per_host = {}
for flow in flow_list:
    src = flow["src"]
    if src not in flows_per_host:
        flows_per_host[src] = [flow]
    else:
        flows_per_host[src].append(flow)

#time at which all servers will consider start_time as 0
sync_time = time.time() + 5

#send them to servers
for host,flows in flows_per_host.iteritems():
    # stop flows being sent
    client.send({"type": "terminate"}, src)

    #send flows bulck
    cmd = {"type":"flowsBulck", "data":flows, "startingTime":sync_time}
    client.send(cmd, host)




