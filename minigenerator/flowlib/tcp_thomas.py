import socket
import time
from minigenerator.misc.utils import send_msg
import subprocess, os , signal

def sendFlowTCP(dst='8.0.0.2',dport=5001,sport=6000,inter_packet_delay=0.2,duration=10,**kwargs):


    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    #s.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, 1500)

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

        startTime = time.time()
        i = 0
        while (time.time() - startTime <= totalTime):
            send_msg(s,"A"*100)
            i +=1
            next_send_time = startTime + i * inter_packet_delay
            time.sleep(max(0,next_send_time - time.time()))

    except socket.error:
        pass

    finally:
        s.close()


def recvFlowTCP(dport=5001,**kwargs):

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


def receiveTCP_netcat(dport=5001,**kwargs):
    def signal_term_handler(signal,frame):
        p.kill()
        p.wait()
        os._exit(0)

    signal.signal(signal.SIGTERM,signal_term_handler)

    p = subprocess.Popen(["nc", "-l", str(dport)], stdout=open(os.devnull, "w"))
    p.wait()
