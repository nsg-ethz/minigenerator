import socket
import os
import errno
import threading
try:
    import cPickle as pickle
except:
    import pickle

from minigenerator import tmp_path as tmp_files
from minigenerator.misc.utils import send_msg,recv_msg

class UnixClientTCP(object):

    def __init__(self,server_address_base = tmp_files+"learningServer_{0}"):

        self.server_address_base = server_address_base
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        #if its empty it means that we are not connected to anything
        self.connected_server = ""

    def createSocket(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def close(self):

        self.connected_server = ""
        self.sock.close()

    def connect(self,server):

        if not self.connected_server:
            self.createSocket()
            self.sock.connect(self.server_address_base.format(server))
            self.connected_server = server

        elif self.connected_server != server:
            self.close()
            self.connect(server)


    def send(self,msg,server):

        reconnections = 3
        while reconnections:
            try:
                #creates socket and connects if necessary
                self.connect(server)
                send_msg(self.sock,pickle.dumps(msg))
                #breaks the while
                break

            except socket.error as serr:
                reconnections -=1
                self.connected_server = ""
                if serr.errno != errno.ECONNREFUSED and serr.errno != errno.EPIPE and serr.errno != errno.ENOENT:
                    raise serr
                else:
                    print serr
                    print "Server {1}{0} could not be reached. Trying again...".format(server,self.server_address_base)

        if not reconnections:
            raise socket.error

    def sendAndClose(self,msg,server):

        self.send(msg,server)
        self.close()


class UnixServerTCP(object):

    def __init__(self,address,queue):

        self.server_address = address
        try:
            os.unlink(self.server_address)
        except OSError:
            if os.path.exists(self.server_address):
                raise

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)

        self.sock.listen(200)

        self.queue = queue


    def close(self):

        self.sock.close()
        os.remove(self.server_address)


    def handleConnection(self,conn,queue):

        message = recv_msg(conn)
        while message:
            queue.put(pickle.loads(message))
            message = recv_msg(conn)

        conn.close()

    def receive(self):

        return self.sock.recv(1024)


    def runThread(self):

        p = threading.Thread(target=self.run)
        p.setDaemon(True)
        p.start()

    def run(self):

        try:
            while True:
                conn, addr = self.sock.accept()

                p =threading.Thread(target=self.handleConnection,args=(conn,self.queue))
                p.setDaemon(True)
                p.start()
        except:
            self.close()



class UnixClient(object):

    def __init__(self,server_address_base = tmp_files+"flowServer_{0}"):

        self.server_address_base = server_address_base

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)


    def close(self):

        self.sock.close()


    def send(self,m,server):
        try:
            self.sock.sendto(pickle.dumps(m),self.server_address_base.format(server))
        except socket.error as serr:
            print serr
            print "Server {0} could not be reached".format(self.server_address_base.format(server))
            #log.info("Server {0} could not be reached".format(server))

class UnixServer(object):

    def __init__(self,address):

        self.server_address = address
        try:
            os.unlink(self.server_address)
        except OSError:
            if os.path.exists(self.server_address):
                raise
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(self.server_address)


    def close(self):

        self.sock.close()
        os.remove(self.server_address)

    def receive(self):

        return pickle.loads(self.sock.recv(8128))

