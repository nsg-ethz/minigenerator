"""
Example of how to send single flow commands to flow servers

This example generates a random bijective traffic pattern, where each host sends a flow.
 
All flows are tcp, with a duration set to 10 seconds and maximum interface rate

"""
from minigenerator.misc.unixsockets import UnixClient
from minigenerator.misc.topology import Topology
from minigenerator import udp_server_address, topology_path
import random

#load topology
topo = Topology(db=topology_path)

#create unix socket client with flow server address (udp)
client = UnixClient(udp_server_address)


#get hosts
hosts = topo.getHosts().keys()
random.shuffle(hosts)

starting_port = 5000

for i, host in enumerate(hosts):
    src = host
    dst = hosts[(i+1)%len(hosts)]

    #get hosts sending rate in mbits
    send_rate = topo.interface_bandwidth(host,"{0}-eth0".format(host))
    #convert it to MBIT/s
    send_rate = "%dM" % send_rate

    flow_template = {"src": src,
                     "dst": dst,
                     "dport": starting_port+i,
                     "sport": starting_port+i,
                     "proto": "TCP",
                     "duration": 10,
                     "size": 0,
                     "rate": send_rate}

    #stop flows being sent
    client.send({"type":"terminate"},src)

    #send flow command
    cmd = {"type":"flow", "data":flow_template}
    client.send(cmd,src)


