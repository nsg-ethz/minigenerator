from mininet.topo import Topo
from mininet.net import Mininet
from mininet.nodelib import LinuxBridge
from mininet.log import setLogLevel, info
from mininet.util import custom
from mininet.link import TCIntf
from minigenerator.minigen import Minigenerator
from minigenerator.cli import MiniGeneratorCLI

class ExampleTopo(Topo):


    def build( self, **_opts ):

        #add linux bridges
        s1, s2, s3 = [ self.addSwitch( s,cls=LinuxBridge ) for s in ( 's1', 's2', 's3' ) ]

        #add 6 hosts (2 per switch)
        h_11, h_12 = [self.addHost(name) for name in ('h_11', 'h_12')]
        h_21, h_22 = [self.addHost(name) for name in ('h_21', 'h_22')]
        h_31, h_32 = [self.addHost(name) for name in ('h_31', 'h_32')]

        #interconnect switches in a triangle
        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s2, s3)

        #connect hosts to switch

        self.addLink(h_11, s1)
        self.addLink(h_12, s1)

        self.addLink(h_21, s2)
        self.addLink(h_22, s2)

        self.addLink(h_31, s3)
        self.addLink(h_32, s3)



def main():

    topo = ExampleTopo()

    intf = custom(TCIntf, bw =100)

    net = Mininet(topo=topo,intf=intf)

    info("*** Starting topology\n")
    net.start()

    info("*** Starting minigenerator\n")
    minigen = Minigenerator(net=net)

    minigen.start()

    MiniGeneratorCLI(net)

    info("*** Stoping minigen and network\n")
    minigen.stop()
    net.stop()



if __name__ == '__main__':

    setLogLevel('info')
    main()