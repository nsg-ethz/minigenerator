from minigenerator.misc.topology import TopologyDB
from minigenerator import topology_path

import mininet.log as l
l.setLogLevel('info')
log = l.lg

class Minigenerator(object):

    def __init__(self,net=None, stored_topology=None, topology_type="TopologyGraph",
                 send_function="send_flow",recv_function="recv_flow",*args,**kwargs):

        self.mininet = net
        self.load_topodb(net=net,stored_topology=stored_topology)


    def load_topodb(self,net,stored_topology):

        TopologyDB(net=net,db=stored_topology).save(topology_path)

    def start(self):

        for host in self.mininet.hosts:
            cmd = ""
            host.cmd(cmd)

    def stop(self):
        pass



