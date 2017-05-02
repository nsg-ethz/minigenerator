import time
import socket
import math
from minigenerator.misc.utils import setSizeToInt

#thats what I get checking wireshark and the ovs switches
#in theory it should be 54
minSizeUDP = 42
maxUDPSize = 65000
PACKET_SIZE =  5000

def sendRate(s,dst,dport,bytesPerSec,packetSize=None):

    """
    Sends BytesPerSec using packets with size = packetSize (65k if not set). If you are sending UDP
    flows in a relatively slow network (i.e 10~100Mbit/s) using this function with a small packet size can
    lead to a huge packet drop at the hosts's default qdisc queue (Fast FIFO) with length tipically 1000 packets. If you
    push all the packets as fast as possible into the hosts software queue without distributing them uniformily during
    1 second if queueing rate is bigger than dequeue drops will start happening.

    If you have problems with that, use sendRate_batch that tries to solve this problem (see below).

    :param s:
    :param dst:
    :param dport:
    :param bytesPerSec:
    :param packetSize:
    :return:
    """

    if not packetSize:
        maxSize = maxUDPSize
    else:
        maxSize = packetSize
    times = math.ceil(float(bytesPerSec) / (maxSize+minSizeUDP))
    time_step= 1/times
    start = time.time()
    i = 0

    print bytesPerSec
    while bytesPerSec > minSizeUDP:
        bytesPerSec -= (s.sendto("A" * min(maxSize, bytesPerSec - minSizeUDP), (dst, dport)) + minSizeUDP)
        i +=1
        next_send_time = start + i * time_step
        time.sleep(max(0,next_send_time - time.time()))
    print bytesPerSec
    print time.time()-start
    time.sleep(max(0,1-(time.time()-start)))

def sendRate_batch(s,dst,dport,bytesPerSec,packetSize=None,packets_round=1):

    """
    To avoid packet drop at the operating system queues when pushing packets to the queues at a faster rate than
    sending them to the network we try to enqueue them few by few along 1 second giving time to the host to empty
    the queue.

    :param s:
    :param dst:
    :param dport:
    :param bytesPerSec:
    :param packetSize:
    :param packets_round:
    :return:
    """

    if not packetSize:
        maxSize = maxUDPSize
    else:
        maxSize = packetSize

    times = math.ceil((float(bytesPerSec) / (maxSize+minSizeUDP))/packets_round)
    time_step= 1/times
    start = time.time()
    i = 0
    while bytesPerSec > minSizeUDP:
        for _ in range(packets_round):
            bytesPerSec -= (s.sendto("A"*min(maxSize,bytesPerSec-minSizeUDP),(dst,dport)) + minSizeUDP)
        i +=1
        next_send_time = start + (i * time_step)
        time.sleep(max(0,next_send_time - time.time()))
    time.sleep(max(0,1-(time.time()-start)))


def sendFlowUDP(dst="10.0.32.2",sport=5000,rate='10M',dport=5001,duration=10,**kwargs):

    """
    Sends a UDP flow at a constant rate in Mbit/s for a given period of time.
    :param dst:
    :param sport:
    :param rate:
    :param dport:
    :param duration:
    :param kwargs:
    :return:
    """

    rate = setSizeToInt(rate)/8

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('',sport))

    totalTime = int(duration)
    try:
        startTime = time.time()
        while (time.time() - startTime < totalTime):
            #Read sendRate_batch comments to know why do we use it
            sendRate_batch(s,dst,dport,rate,packetSize=PACKET_SIZE, packets_round=5)

    finally:
        s.close()

def recvFlowUDP(*args,**kwargs):
    pass