#!/usr/bin/python
import sched
import multiprocessing
import time
import traceback
import signal
import sys
from threading import Thread
import Queue

from minigenerator import udp_server_address, tcp_server_address, flow_server_name, topology_path
from minigenerator.misc.unixsockets import UnixServer, UnixServerTCP
from minigenerator.flowlib.tcp import recvFlowTCP
from minigenerator.misc.utils import KThread

MAX_PORT = 2**16 -1


#HELPER CLASS
class Joiner(Thread):
    """
    Joiner class that tries to join (to avoid zombies)
    all the processes that are being queued into the queue.
    Note that if you join a very long process, the rest have to wait
    to be joined.
    """
    def __init__(self, q):
        super(Joiner,self).__init__()
        self.__q = q
    def run(self):
        while True:
            child = self.__q.get()
            if child == None:
                return
            child.join()

class FlowServer(object):

    def __init__(self,name,topology,send_function,recv_function=recvFlowTCP):

        ##
        #SERVER NAME
        self.name = name

        ##
        #COMMUNICATION

        #The flow server is listening to commands through several servers. We use unix sockets (that use the file system),
        #due to mininet networks are typically lunched in a single machine sharing file system.
        #One server listens to UDP packets (for small commands), while the other can handle big chunks of data using TCP.

        #we need a queue for events
        self._server_queue = Queue.Queue(0)

        self._server = UnixServer(udp_server_address.format(name))
        self._server_tcp = UnixServerTCP(tcp_server_address.format(name), self._server_queue)

        #start UDP server thread
        p = Thread(target=self._serverUDPListener,args=(self._server,self._server_queue,))
        p.setDaemon(True)
        p.start()

        #start tcp listener
        # start TCP server that listens for events and queues them in the server_queue
        self.server_tcp.runThread()

        #TODO: add suport for AF_INET sockets

        ##
        #PROCESSES handling

        #Flow process containers
        self._processes = []
        self._processes_TCPServers = []

        #Singal handler
        signal.signal(signal.SIGTERM,self.signal_term_handler)

        #Store process id. Used to differenciate the SIGTERM signal between the server and child processes.
        self.parentPid = os.getpid()
        log.debug_high("Parent pid and process pid:{0},{1}".format(os.getppid(), os.getpid()))

        ##
        #TOPOLOGY
        #TODO: explain how to use a topology object
        self.topology = topology(db=topology_path)

        ##
        #SEND AND RECEIVE FUNCTIONS
        self.send_funct = send_function
        self.recv_funct = recv_function

        ##
        #Start process joiner, keeps a queue with processes and tries to join them sequentially.
        self._joiner_queue = Queue.Queue(maxsize=0)
        joiner =Joiner(self._joiner_queue)
        joiner.setDaemon(True)
        joiner.start()



    #thread that listens for UDP events and queues them in the main queue
    def serverUDPListener(self,server,queue):
        while True:
            event = server.receive()
            queue.put(event)


    def signal_term_handler(self,signal,frame):
        #only parent will do this
        if os.getpid() == self.parentPid:
            self.server.close()
            self.server_tcp.close()
            os._exit(0)
        else:
            os._exit(0)

    def terminateALL(self):
        # for process in self.processes
        #kill start flows thread if it exists
        if hasattr(self,"scheduler_thread"):
            try:
                self.scheduler_thread.kill()
            except Exception:
                traceback.print_exc()

        #send processes
        for process in self.processes:
            if process.is_alive():
                try:
                    time.sleep(0.001)
                    process.terminate()
                    process.join()
                except OSError:
                    log.warning("Problem killing sender's processes")

        #receive processes
        for process in self.processes_TCPServers:
            try:
                process.terminate()
                process.join()
            except OSError:
                log.warning("Problem killing receiver's processes")

        self.processes_TCPServers = []
        self.processes = []

    def startFlow(self,flow):

        #we add some extra parameters that can be useful to flow: (sender and receiver names)
        flow.update({"dst_host_name": self.topology.getHostName(flow["dst"]), "src_host_name":self.name})

        # start flow process
        process = multiprocessing.Process(target=self.send_funct, kwargs=(flow))
        process.daemon = True
        process.start()

        self.processes.append(process)
        self.queue.put(process)



    def startReceiveTCP(self,port):

        """
        Starts a TCP server that waits until a single sender connects,
        transmits data, and closes the connection.
        

        :param port:
        :return:
        """

        process = multiprocessing.Process(target=self.recv_funct,args=(int(port),))
        process.daemon = True
        process.start()

        self.processes_TCPServers.append(process)
        self.queue.put(process)

    def startFlowsBulck(self,flows,startingTime):

        scheduler = sched.scheduler(time.time,time.sleep)

        for flow in flows:
            scheduler.enter(flow["start_time"],1,self.startFlow,[flow])

        #sleep until starting time
        sleeping_time = startingTime - time.time()
        if sleeping_time < 0:
            log.warining("Sleeping Time smaller than 0")
            sleeping_time = 0
        log.debug_high("Sleeping time before getting sync: {0} {1}".format(self.name, sleeping_time))
        time.sleep(sleeping_time)

        #start a thread with the scheduler run
        self.scheduler_thread = KThread(target=scheduler.run)
        self.scheduler_thread.setDaemon(True)
        self.scheduler_thread.start()


    def run(self):

        """
        Waits for new commands, executes them and waits again.
        :return: None
        """

        while True:

            #Read event from the queue
            event = self.server_queue.get()
            self.server_queue.task_done()


            log.debug_medium("FlowServer({0}) -> Received event: {1}".format(self.name,str(event)))

            ############################################
            # EVENTS LIST
            ############################################

            if event["type"] == "terminate":
                self.terminateALL()

            elif event["type"] == "TCPServer":
                self.startReceiveTCP(str(event["port"]))

            elif event["type"] == "flow":
                flow = event["data"]

                #Calls start flow function
                self.startFlow(flow)

            elif event["type"] == "flowsBulck":
                flows = event["data"]
                startingTime = event["startingTime"]

                #schedule all the flows
                self.startFlowsBulck(flows,startingTime)

            else:
                log.warning("Unknown event {0}".format(event))


if __name__ == "__main__":

    import os
    from minigenerator.logger import log
    import logging
    name = sys.argv[1]

    _topology = sys.argv[2]
    _send = sys.argv[3]
    _recv = sys.argv[4]

    import importlib

    #TODO: this fix topologies and send recv functions to be defined always in the same file, should make this flexible
    topology = getattr(importlib.import_module("minigenerator.misc.topology"),_topology)
    send_function = getattr(importlib.import_module("minigenerator.flowlib.customflows"),_send)
    recv_function = getattr(importlib.import_module("minigenerator.flowlib.customflows"),_recv)


    #store the pid of the process so we can stop it when we stop the network
    with open(flow_server_name.format(name)+".pid","w") as f:
        f.write(str(os.getpid()))

    #setting logger level and initial message
    log.setLevel(logging.DEBUG)
    log.info("Starting Flows Server {0}".format(name))


    FlowServer(name,topology,send_function,recv_function).run()