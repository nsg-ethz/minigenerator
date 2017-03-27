#!/usr/bin/python
import sched
import multiprocessing
import time
try:
    import cPickle as pickle
except:
    import pickle
import signal
import sys
from threading import Thread
import Queue

from minigenerator import tmp_path as tmp_files
from minigenerator import udp_server_address, tcp_server_address
from minigenerator.misc.unixSockets import UnixServer, UnixServerTCP
from minigenerator.flowlib.tcp import recvFlowTCP
from minigenerator.misc.utils import KThread

MAX_PORT = 2**16 -1


#HELPER CLASS
class Joiner(Thread):
    """
    Joiner class that tries to join (to avoid zombies)
    all the processes that are being queued into the queue.
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


        self.name = name

        #sockets to receiver commands
        #I WILL KEEP A UDP SOCKET AND TCP SOCKET LISTENING. UDP IS USED FOR SMALL THINGS, TCP IS ONLY USED WHEN THE
        #OBJECT I WANT TO SEND CAN BE QUITE BIG
        self.server = UnixServer(udp_server_address.format(name))

        #we need a queue for events
        self.server_queue = Queue.Queue(0)

        #start TCP server that listens for events and queues them in the server_queue
        self.server_tcp  = UnixServerTCP(udp_server_address.format(name),self.server_queue)

        #start UDP server thread
        p = Thread(target=self.serverUDPListener,args=(self.server_queue,))
        p.setDaemon(True)
        p.start()

        #start tcp listener
        self.server_tcp.runThread()

        ###########################################################

        #Flow process containers
        self.processes = []
        self.processes_TCPServers = []

        #Singal handler
        signal.signal(signal.SIGTERM,self.signal_term_handler)
        #signal.signal(signal.SIGCHLD,signal.SIG_IGN)

        #PARENT PID
        self.parentPid = os.getpid()
        log.debug_high("First time p:{0},{1}".format(os.getppid(), os.getpid()))

        #topology
        #Here you habve two options you can use my TopologyGraph object,
        # or just a simple object that has the method getHostName(hostip)

        #
        # self.topology = TopologyGraph(loadNetworkGraph=True, getIfNames=False, getIfindexes=False, snmp=False,
        #                          openFlowInformation=False, hostsMappings=True, interfaceToRouterName=False,
        #                          db=os.path.join(tmp_files, db_topo))

        self.topology = topology
        self.send_funct = send_function
        self.recv_funct = recv_function

        #start joiner
        self.queue = Queue.Queue(maxsize=0)
        joiner =Joiner(self.queue)
        joiner.setDaemon(True)
        joiner.start()

        #tcp server application
        self.TCPreceiver_type = "socket"


    #thread that listens for UDP events and queues them in the main queue
    def serverUDPListener(self,queue):
        while True:
            event = self.server.receive()
            queue.put(event)


    def signal_term_handler(self,signal,frame):
        #only parent will do this
        if os.getpid() == self.parentPid:
            #self.queue.put(None)
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
                import traceback
                traceback.print_exc()


        for process in self.processes:

            if process.is_alive():
                try:
                    time.sleep(0.001)
                    process.terminate()
                    process.join()
                except OSError:
                    pass

        for process in self.processes_TCPServers:
            if self.TCPreceiver_type != "nc":
                process.terminate()
                process.join()
            else:
                process.kill()
                process.wait()

        #kill nc processes
        self.processes_TCPServers = []
        self.processes = []

    def startFlow(self,flow):

        remoteServer = ""
        # add the host name into the flow that  is needed to generate TCP flows so the client starts the server
        if flow["proto"] == "TCP":
            remoteServer= self.topology.getHostName(flow["dst"])

        # start flow process
        process = multiprocessing.Process(target=self.send_funct,args=(self.name,remoteServer), kwargs=(flow))
        process.daemon = True
        process.start()

        self.processes.append(process)
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





    def startReceiveTCP(self,port):

        """
        Starts a TCP server that waits until a single sender connects,
        transmits data, and closes the connection.

        Different ways of listening tcp traffic have been considered. Net cat uses less cpu on average than our minimal
        python implementation, however popen sometimes (when starting a big amount of flows gets stuck, could not find
        the reason). Alternatively we use very simple TCP server implemented in pure python.

        :param port:
        :return:
        """

        if self.TCPreceiver_type == "nc":
            os.system("nc -l -p {0} >/dev/null 2>&1 &".format(port))
            #process = subprocess.Popen(["nc", "-l", port], stdout=open(os.devnull, "w"))
            #process = subprocess.Popen("nc -l -p {port} &".format(port=port), stdout=open(os.devnull, "w"), shell=True)
            #self.processes_TCPServers.append(process)
            #self.queue.put(process)
        else:
            # start flow process
            process = multiprocessing.Process(target=self.recv_funct,args=(int(port),))
            process.daemon = True
            process.start()

            self.processes_TCPServers.append(process)
            self.queue.put(process)

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
                log.warning("unknown event {0}".format(event))


if __name__ == "__main__":

    import os
    from minigenerator.logger import log
    import logging


    name = sys.argv[1]

    #store the pid of the process so we can stop it when we stop the network
    with open("/tmp/flowServer_{0}.pid".format(name),"w") as f:
        f.write(str(os.getpid()))

    #setting logger level and initial message
    log.setLevel(logging.DEBUG)
    log.info("Starting Flows Server {0}".format(name))


    FlowServer(name).run()