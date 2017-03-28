import time
import socket
import threading
import traceback
from minigenerator.misc.unixSockets import UnixClient, UnixClientTCP
from minigenerator.flowlib.tcp import sendFlowTCP
from minigenerator.flowlib.udp import sendFlowUDP

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


def sendFlowTCP_withServer(dst="10.0.32.3",sport=5000,dport=5001,size = "10M",rate="0M",duration=0,host="h_0_0",**kwargs):

    #start_server
    now = time.time()

    tcp_data = {"host":host, "dport":dport}
    tcp_thread = StartTCPServerThread(tcp_data)
    tcp_thread.setDaemon(True)
    tcp_thread.start()
    time.sleep(max(0, 1 - (time.time() - now)))

    sendFlowTCP(dst=dst,sport=sport,dport=dport,size =size,rate=rate,duration=duration,**kwargs)


def sendFlowAndDetect(serverName, remoteServerName, **flow):

    """
    :param serverName:
    :param remoteServerName:
    :param flow:
    :return:
    """

    client = UnixClientTCP("/tmp/flowDetection_{0}".format(serverName))
    client_tg = UnixClientTCP("/tmp/trafficGenerator")

    try:
        # start server, this was done before in the function sendFlowTCP with server. I moved it here so I can start the server
        # and do the traceroute much earlier than before, even before notifying the flow to the controller.
        if flow["proto"] == "TCP":
            tcp_data = {"host": remoteServerName, "dport": flow["dport"]}
            startTCPServer(**tcp_data)

            # give time to the server to start listening
            time.sleep(1)

        # nofity flow detector if elephant
        if flow["duration"] >= 20:
            client.send({"type": "startingFlow", "flow": flow}, "")


        if flow["proto"] == "UDP":

            # time.sleep(max(0, 1 - (time.time() - now)))
            # start flow
            sendFlowUDP(**flow)

        elif flow["proto"] == "TCP":

            file_name = evaluation_path + "flowDurations/{0}_{1}_{2}_{3}".format(flow["src"], flow["sport"],
                                                                                    flow["dst"], flow["dport"])
            # save flow starting time
            with open(file_name, "w") as f:
                f.write(str(time.time()) + "\n")

            sendFlowTCP(**flow)

            # save flow stopping time
            with open(file_name, "a") as f:
                f.write(str(time.time()) + "\n")

        # send a stop notification to the controller for that elephant flow
        if flow["duration"] >= 20:
            client.sendAndClose({"type": "stoppingFlow", "flow": flow}, "")

            #NOTIFY TRAFFIC GENERATOR REMOVE IF YOU DONT USE THAT
            try:
                client_tg.sendAndClose("stoppingFlow", "")
            except socket.errno:
                pass

    except Exception:
        traceback.print_exc()
        pass

    finally:
        client.sock.close()

def sendFlow(remoteServerName,**flow):

    """
    :param serverName:
    :param remoteServerName:
    :param flow:
    :return:
    """

    try:
        # start server, this was done before in the function sendFlowTCP with server. I moved it here so I can start the server
        # and do the traceroute much earlier than before, even before notifying the flow to the controller.
        if flow["proto"] == "TCP":
            tcp_data = {"host": remoteServerName, "dport": flow["dport"]}
            startTCPServer(**tcp_data)

            # give time to the server to start listening
            time.sleep(1)

        if flow["proto"] == "UDP":

            # time.sleep(max(0, 1 - (time.time() - now)))
            # start flow
            sendFlowUDP(**flow)

        elif flow["proto"] == "TCP":

            file_name = evaluation_path + "flowDurations/{0}_{1}_{2}_{3}".format(flow["src"], flow["sport"],
                                                                                    flow["dst"], flow["dport"])
            # save flow starting time
            with open(file_name, "w") as f:
                f.write(str(time.time()) + "\n")

            sendFlowTCP(**flow)

            # save flow stopping time
            with open(file_name, "a") as f:
                f.write(str(time.time()) + "\n")

    except Exception:
        traceback.print_exc()
        pass

    finally:
        pass

# FUNCTION THAT SENDS FLOWS HERE WE SPECIFY IF ITS TCP OR UDP
def sendFlowNotifyController(**flow):
    # store time so we sleep 1 seconds - time needed for the following commands
    now = time.time()

    client = UnixClient("/tmp/controllerServer")

    try:
        # start server, this was done before in the function sendFlowTCP with server. I moved it here so I can start the server
        # and do the traceroute much earlier than before, even before notifying the flow to the controller.
        if flow["proto"] == "TCP":
            now = time.time()
            tcp_data = {"host": flow["host"], "dport": flow["dport"]}
            tcp_thread = StartTCPServerThread(tcp_data)
            tcp_thread.setDaemon(True)
            tcp_thread.start()

        # nofity the controler if elephant
        if flow["duration"] >= 20:
            # notify controller that a flow will start
            # we wait so we have time to get the traceroute data
            time.sleep(max(0, 1 - (time.time() - now)))
            client.send({"type": "startingFlow", "flow": flow}, "")

        else:
            pass

        if flow["proto"] == "UDP":

            time.sleep(max(0, 1 - (time.time() - now)))
            # start flow
            sendFlowUDP(**flow)

        elif flow["proto"] == "TCP":

            # sendFlowTCP_withServer(**flow)

            # file_name = lb.lb_path+"/evaluation/flowDurations/{0}_{1}_{2}_{3}".format(flow["src"],flow["sport"],flow["dst"],flow["dport"])
            # #save flow starting time
            # with open(file_name,"w") as f:
            #     f.write(str(time.time())+"\n")

            sendFlowTCP(**flow)

            # save flow stopping time
            # with open(file_name,"a") as f:
            #     f.write(str(time.time())+"\n")

        # send a stop notification to the controller for that elephant flow
        if flow["duration"] >= 20:
            client.send({"type": "stoppingFlow", "flow": flow}, "")

    except Exception:

        traceback.print_exc()
        pass

    finally:
        client.sock.close()



