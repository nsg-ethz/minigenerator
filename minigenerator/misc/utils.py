import struct
import socket
import fcntl
import os
import threading
import sys

def is_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def read_pid(file_name):
    """
    Extract a pid from a file
    :param n: path to a file
    :return: pid as a string
    """
    try:
        with open(file_name, 'r') as f:
            return str(f.read()).strip(' \n\t')
    except:
        return None

def del_file(f):
    try:
        os.remove(f)
    except OSError:
        pass

def setSizeToInt(size):
    """" Converts the sizes string notation to the corresponding integer
    (in bytes).  Input size can be given with the following
    magnitudes: B, K, M and G.
    """
    if isinstance(size, int):
        return size
    elif isinstance(size,float):
        return int(size)
    try:
        conversions = {'B': 1, 'K': 1e3, 'M': 1e6, 'G': 1e9}
        digits_list = range(48,58) + [ord(".")]
        magnitude = chr(sum([ord(x) if (ord(x) not in digits_list) else 0 for x in size]))
        digit = float(size[0:(size.index(magnitude))])
        magnitude = conversions[magnitude]
        return int(magnitude*digit)
    except:
        return 0

#Helpers to send big packets
def send_msg(sock, msg):

    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)

def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = ''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None

        data += packet
    return data

def isTCP(flow):

    return flow["proto"].upper() == "TCP"

def isUDP(flow):

    return flow["proto"].upper() == "UDP"


class KThread(threading.Thread):
  """A subclass of threading.Thread, with a kill()
method."""
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False

  def start(self):
    """Start the thread."""
    self.__run_backup = self.run
    self.run = self.__run      # Force the Thread to install our trace.
    threading.Thread.start(self)

  def __run(self):
    """Hacked run function, which installs the
trace."""
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup

  def globaltrace(self, frame, why, arg):
    if why == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, why, arg):
    if self.killed:
      if why == 'line':
        raise SystemExit()
    return self.localtrace

  def kill(self):
    self.killed = True

#RAW Socket Object, used to craft udp and tcp (without being connected).
class RawSocket(object):
    def __init__(self):

        #open a tcp and udp raw socket.
        self.open()

        #since this object was implemented to craft udp and tcp traffic to gather netflow data we were only
        #interested on changing few parameters such as (ttl, ip addresses and ports). Thus to fast craft packets
        #we consider the rest as a constant for every packet we send.

        self.ip_constant = self._ip_header_constant()
        self.tcp_constant = self._tcp_header_constant()

        #gets eth0 ip address
        try:
            self.src = self.get_ip_address(self.getInterfaceName())
        except:
            self.src = ""


    def close(self):
        self.tcp_socket.close()
        self.udp_socket.close()

    def open(self):
        #Initializes sockets we will use
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("tcp"))
        self.tcp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("udp"))
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    def get_ip_address(self,ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

    def getInterfaceName(self):
        # assume host only has eth0
        return [x for x in os.listdir('/sys/class/net') if "eth0" in x][0]


    def _ip_header_constant(self):
        # ip header fields
        ihl = 5
        version = 4
        tos = 128
        tot_len = 20 + 20   # python seems to correctly fill the total length, dont know how ??
        id = 54321  #Id of this packet
        frag_off = 0
        ihl_version = (version << 4) + ihl

        # the ! in the pack format string means network order
        ip_header = struct.pack('!BBHHH' , ihl_version, tos, tot_len, id, frag_off)
        return ip_header

    def _tcp_header_constant(self):
        seq = 0
        ack_seq = 0
        doff = 5    #4 bit field, size of tcp header, 5 * 4 = 20 bytes
        #tcp flags
        fin = 0
        syn = 1
        rst = 0
        psh = 0
        ack = 0
        urg = 0
        window = socket.htons (5840)    #   maximum allowed window size
        urg_ptr = 0

        offset_res = (doff << 4) + 0
        tcp_flags = fin + (syn << 1) + (rst << 2) + (psh <<3) + (ack << 4) + (urg << 5)
        tcp_checksum = 0

        # make the tcp header again and fill the correct checksum
        tcp_header = struct.pack('!LLBBHHH' ,seq, ack_seq, offset_res, tcp_flags,  window, tcp_checksum , urg_ptr)

        # final full packet - syn packets dont have any data
        return tcp_header

    def _ip_header_variable(self,src,dst,ttl,proto):

        if proto == "tcp":
            proto = socket.IPPROTO_TCP
        elif proto == "udp":
            proto = socket.IPPROTO_UDP
        else:
            print "proto unknown"
            return
        check = 10  # python seems to correctly fill the checksum
        saddr = socket.inet_aton ( src )  #Spoof the source ip address if you want to
        daddr = socket.inet_aton ( dst )
        # the ! in the pack format string means network order
        ip_header = struct.pack('!BBH4s4s' , ttl, proto, check, saddr, daddr)
        return ip_header


    def _udp_header(self,sport,dport):
        sport = sport    # arbitrary source port
        dport = dport   # arbitrary destination port
        #length = 8;
        #checksum = 0
        header = struct.pack('!HHHH', sport, dport, 8, 0)
        return header

    def _tcp_header_variable(self,sport,dport):

        # tcp header fields
        source = sport #sourceport
        dest = dport  # destination port

        tcp_header = struct.pack('!HH' , source, dest)

        # final full packet - syn packets dont have any data
        return tcp_header

    def sendto(self,src=None,dst="10.0.32.2",sport=5555,dport=5555,ttl=5,proto="udp"):
        #get default source address
        if not src:
            src = self.src

        header = self.ip_constant + self._ip_header_variable(src, dst, ttl, proto)
        if proto =="udp":
            header += self._udp_header(sport,dport)
            #send packet
            self.udp_socket.sendto(header, (dst, 0))
        elif proto =="tcp":
            header += (self._tcp_header_variable(sport, dport) + self.tcp_constant)
            self.tcp_socket.sendto(header, (dst, 0))