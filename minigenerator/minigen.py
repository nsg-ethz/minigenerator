from minigenerator.misc.topology import TopologyDB
from minigenerator.misc.unixsockets import UnixClient
from minigenerator.misc.utils import read_pid, del_file
from minigenerator import topology_path, flowserver_path, \
                                      udp_server_address, \
                                      flow_server_name, \
                                      tcp_server_address

import mininet.log as l
l.setLogLevel('info')
log = l.lg

class Minigenerator(object):

    def __init__(self,net=None, stored_topology=None, topology_type="TopologyGraph",
                 send_function="send_flow",recv_function="recv_flow",*args,**kwargs):

        self.mininet = net
        self.load_topodb(net=net,stored_topology=stored_topology)
        self._topology = topology_type
        self._send_funct = send_function
        self._recv_funct = recv_function


    def load_topodb(self,net,stored_topology):

        TopologyDB(net=net,db=stored_topology).save(topology_path)

    def start(self):
        log.info('*** Starting Minigenerator Servers\n')
        for host in self.mininet.hosts:
            cmd = flowserver_path+" {0} {1} {2} {3} &".format(host.name,
                                                            self._topology,
                                                            self._send_funct,
                                                            self._recv_funct)
            #lunches flowserver
            host.cmdPrint(cmd)

    def stop(self):
        log.info('*** Stopping Minigenerator Servers\n')

        client = UnixClient(udp_server_address)

        for host in self.mininet.hosts:

            #send a termiante command so all the ongoing flows are gracefully
            #sends a command to the server to kill it
            client.send({"type":"softKill"},host.name)

            #in case that this does not work we try with the pid and kill -9

            #read flowserver pid
            pid = read_pid(flow_server_name.format(host.name)+".pid")

            if pid:
                log.debug('Killing Flow Server at host : {0}'.format(host.name))
                host.cmd('kill','-9', pid)

            #we erase all the possible files created by the server
            #pid file
            del_file(flow_server_name.format(host.name)+".pid")
            #udp unix socket server
            del_file(udp_server_address.format(host.name))
            #tcp unix socket server
            del_file(tcp_server_address.format(host.name))
