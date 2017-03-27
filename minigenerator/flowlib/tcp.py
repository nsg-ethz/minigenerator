import socket
import time
from minigenerator.misc.utils import setSizeToInt, send_msg
import subprocess, os , signal
minSizeTCP = 66

def sendFlowTCP(dst="10.0.32.3",sport=5000,dport=5001,size = "10M",rate="0M",duration=0,**kwargs):

    totalSize = setSizeToInt(size)/8
    rate = setSizeToInt(rate)/8
    headers_overhead = minSizeTCP * (rate / 4096)
    headers_overhead_total = minSizeTCP * (totalSize / 4096)
    rate = rate - (headers_overhead)
    totalSize = totalSize - (headers_overhead_total)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, 1500)
    s.bind(('', sport))
    try:
        reconnections = 5
        while reconnections:
            try:
                s.connect((dst, dport))
                break
            except:
                reconnections -=1
                print "TCP flow client could not connect with server... Reconnections left {0} ...".format(reconnections)
                time.sleep(0.5)

        #could not connect to the server
        if reconnections == 0:
            return



        totalTime = int(duration)

        #if total size is set to 0 the we use duration time and rate (which can be less than the maximum link rate)
        if not totalSize:
            startTime = time.time()
            i = 0
            time_step = 1
            while (time.time() - startTime <= totalTime):
                send_msg(s,"A"*rate)
                i +=1
                next_send_time = startTime + i * time_step
                time.sleep(max(0,next_send_time - time.time()))
                #print time.time()-startTime


        # IMPORTANT NOTE: instead of pushing bytes into the socket every second, you can use socket.sendall(totalsize)
        # however that drastically increases CPU usage at the time of running the send command, something we want to avoid
        # since multiple hosts could be creating flows in parallel (if we emulate them in the same machine) causing problems
        # to other applications.


        #we send the size in bytes at the rate rate as maximum
        else:
            startTime = time.time()
            i = 0
            time_step = 1
            while (totalSize > minSizeTCP):
                rate = min(rate, totalSize - minSizeTCP)
                send_msg(s,"A"*rate)
                totalSize -= rate
                i +=1
                next_send_time = startTime + i * time_step
                time.sleep(max(0,next_send_time - time.time()))
            #print "flow duration {0}, src: {1}:{2}, dst {3}:{4} with size: {5}".format(time.time()-startTime,kwargs["src"],dst,sport,dport,size)

    except socket.error:
        pass

    finally:
        s.close()


def recvFlowTCP(dport=5001):

    """
    Lisitens on port dport until a client connects sends data and closes the connection. All the received
    data is thrown for optimization purposes.
    :param dport:
    :return:
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.bind(("", dport))
    s.listen(1)
    conn = ''
    buffer = bytearray(4096)
    try:
        conn, addr = s.accept()
        while True:
            #data = recv_msg(conn)#conn.recv(1024)
            if not conn.recv_into(buffer,4096):
                break

    finally:
        if conn:
            conn.close()
        else:
            s.close()

def receiveTCP_netcat(p):
    def signal_term_handler(signal,frame):
        p.kill()
        p.wait()
        os._exit(0)

    signal.signal(signal.SIGTERM,signal_term_handler)

    p = subprocess.Popen(["nc", "-l", str(p)], stdout=open(os.devnull, "w"))
    p.wait()


