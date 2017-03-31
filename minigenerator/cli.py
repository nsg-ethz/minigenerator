from mininet.cli import CLI
from mininet.log import info, output, error
from minigenerator.misc.unixsockets import UnixClient

class MiniGeneratorCLI(CLI):
    
    def __init__(self,minigenerator,*args,**kwargs):

        if minigenerator:
            self.minigenerator = minigenerator

        CLI.__init__(self,*args,**kwargs)


    def do_minigeneratorstart(self,line=""):
        """A  """
        self.minigenerator.start()

    def do_minigeneratorstop(self,line=""):
        self.minigenerator.stop()


    # def do_stoprouter(self,line=""):
    #
    #     """stop zebra and ospf from a router"""
    #     router_name = line.split()
    #     if not router_name or len(router_name) > 1:
    #         error('usage: stoprouter router\n')
    #     else:
    #         router_name = router_name[0]
    #         if router_name not in self.mn:
    #             error("router %s not in the network\n" % router_name)
    #         else:
    #             router = self.mn[router_name]
    #             router.router.delete()
    #
    # def do_startrouter(self,line=""):
    #
    #     """start zebra and ospf from a router"""
    #     router_name = line.split()
    #     if not router_name or len(router_name) > 1:
    #         error('usage: startrouter router\n')
    #     else:
    #         router_name = router_name[0]
    #         if router_name not in self.mn:
    #             error("router %s not in the network\n" % router_name)
    #         else:
    #             router = self.mn[router_name]
    #             router.router.start()
    #
    # def do_rebootquaggas(self, line=""):
    #     """restarts zebra and ospfd from all routers"""
    #
    #     for r in self.mn.routers:
    #         r.router.delete()
    #         r.router.start()
    #
    # def do_rebootquagga(self,line=""):
    #
    #     """restarts zebra and ospf from a router"""
    #     router_name = line.split()
    #     if not router_name or len(router_name) > 1:
    #         error('usage: rebootquagga router\n')
    #     else:
    #         router_name = router_name[0]
    #         if router_name not in self.mn:
    #             error("router %s not in the network\n" % router_name)
    #         else:
    #             router = self.mn[router_name]
    #             router.router.delete()
    #             router.router.start()

