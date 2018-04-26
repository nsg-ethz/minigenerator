from mininet.cli import CLI
from mininet.log import info, output, error
from minigenerator.misc.unixsockets import UnixClient

class MiniGeneratorCLI(CLI):

    def __init__(self,minigenerator,*args,**kwargs):

        if minigenerator:
            self.minigenerator = minigenerator

        CLI.__init__(self,*args,**kwargs)


    def do_minigenerator(self,line=""):
        """Start/stop/restart the mininet generator
           Usage: mininet start/stop/restart node
        """
        args = line.strip().split()
        if len(args) == 2:
            cmd = args[0]
            host = args[1]

            if cmd == "start":
                if host == "all":
                    self.minigenerator.start()
                elif host in self.minigenerator.mininet:
                    self.minigenerator.start_node(host)
                else:
                    error('invalid host')
            elif cmd == "stop":
                if host == "all":
                    self.minigenerator.stop()
                elif host in self.minigenerator.mininet:
                    self.minigenerator.stop_node(host)
                else:
                    error('invalid host')
            elif cmd == "restart":
                if host == "all":
                    self.minigenerator.restart()
                elif host in self.minigenerator.mininet:
                    self.minigenerator.restart_node(host)
                else:
                    error('invalid host')
            else:
                error('invalid command: start stop restart')

        else:
            error('invalid number of args: minigenerator cmd node')

