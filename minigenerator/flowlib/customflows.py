import time
import threading
import traceback
import copy
from minigenerator.misc.unixsockets import UnixClient, UnixClientTCP
from minigenerator.flowlib.tcp import sendFlowTCP, recvFlowTCP
from minigenerator.flowlib.udp import sendFlowUDP
from minigenerator.misc.utils import isTCP, isUDP
from minigenerator import udp_server_address, evaluation_path


#starting tcp server function
def startTCPServer(host, dport):
    flowClient = UnixClient(udp_server_address)
    flowClient.send({"type": "TCPServer", "port": dport}, host)

# starting tcp server thread
class StartTCPServerThread(threading.Thread):
    def __init__(self, tcp_data):
        super(StartTCPServerThread, self).__init__()
        self.tcp_data = tcp_data

    def run(self):
        # sends command to the receiver flow server so it starts a TCP server to listen for the tcp flow.
        flowClient = UnixClient(udp_server_address)
        flowClient.send({"type": "TCPServer", "port": self.tcp_data["dport"]}, self.tcp_data["host"])


def sendFlowTCP_withServer(dst="10.0.32.3",sport=5000,dport=5001,size = "10M",rate="0M",duration=0,dst_host_name="h_0_0",**kwargs):

    #start_server
    now = time.time()

    tcp_data = {"host":dst_host_name, "dport":dport}
    tcp_thread = StartTCPServerThread(tcp_data)
    tcp_thread.setDaemon(True)
    tcp_thread.start()
    time.sleep(max(0, 1 - (time.time() - now)))

    #start flow
    sendFlowTCP(dst=dst,sport=sport,dport=dport,size =size,rate=rate,duration=duration,**kwargs)


def store_duration(function):

    """
    Decorates a sendflow and stores the duration of the flow.
    :param function: 
    :return: 
    """

    def wrapper(*args,**kwargs):
        file_name = evaluation_path + "flowDurations/{0}_{1}_{2}_{3}".format(kwargs["src"], kwargs["sport"],
                                                                                    kwargs["dst"], kwargs["dport"])
        # save flow starting time
        now =time.time()
        res = function(*args,**kwargs)
        with open(file_name, "a") as f:
            f.write(str(time.time()-now) + "\n")
        return res

    return wrapper


def send_flow(dst_host_name,**flow):

    """
    :param serverName:
    :param remoteServerName:
    :param flow:
    :return:
    """

    try:
        # start server, this was done before in the function sendFlowTCP with server. I moved it here so I can start the server
        # and do the traceroute much earlier than before, even before notifying the flow to the controller.
        if isTCP(flow):
            tcp_data = {"host": dst_host_name, "dport": flow["dport"]}
            startTCPServer(**tcp_data)
            # give time to the server to start listening
            time.sleep(1)

        if isUDP(flow):

            sendFlowUDP(**flow)

        elif isTCP(flow):
            #Start flow
            sendFlowTCP(**flow)
    except Exception:
        traceback.print_exc()
        pass

    finally:
        pass

def send_flow_store_duration(dst_host_name,**flow):

    """
    :param serverName:
    :param remoteServerName:
    :param flow:
    :return:
    """

    try:
        # start server, this was done before in the function sendFlowTCP with server. I moved it here so I can start the server
        # and do the traceroute much earlier than before, even before notifying the flow to the controller.
        if isTCP(flow):
            tcp_data = {"host": dst_host_name, "dport": flow["dport"]}
            startTCPServer(**tcp_data)
            # give time to the server to start listening
            time.sleep(1)

        if isUDP(flow):

            sendFlowUDP(**flow)

        elif isTCP(flow):
            #Start flow
            file_name = evaluation_path + "flowDurations/{0}_{1}_{2}_{3}".format(flow["src"], flow["sport"],
                                                                                    flow["dst"], flow["dport"])
            # save flow starting time
            now =time.time()
            sendFlowTCP(**flow)
            with open(file_name, "w") as f:
                f.write(str(time.time()-now) + "\n")
                sendFlowTCP(**flow)

    except Exception:
        traceback.print_exc()
        pass

    finally:
        pass

def recv_flow(*args,**kwargs):
    recvFlowTCP(*args,**kwargs)





