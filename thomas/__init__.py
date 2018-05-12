"""
Mininet has to be installed to use this module
"""
try:
    import mininet
except ImportError as e:
    import sys
    sys.stderr.write('Failed to import mininet!\n'
                     'Using the mininetlib module requires mininet to be '
                     'installed.\n'
                     'Visit www.mininet.org to learn how to do so.\n')
    sys.exit(1)


import os
import ConfigParser
import pkgutil

#path to the configuration directory
RES= os.path.join(os.path.dirname(__file__),'res')

CFG = ConfigParser.ConfigParser()

with open(os.path.join(RES,'config.cfg'),'r') as f:
    CFG.readfp(f)

minigenerator_path = os.path.dirname(__file__)
flowserver_path= pkgutil.get_loader("minigenerator.flowserver").filename


#loads configurations
tmp_path = CFG.get("DEFAULT","tmp_path")
topology_path =CFG.get("DEFAULT","topology_path")
flow_server_name = CFG.get("DEFAULT","flow_server_name")
udp_server_address = CFG.get("DEFAULT","udp_server_address")
tcp_server_address = CFG.get("DEFAULT","tcp_server_address")
evaluation_path =  CFG.get("DEFAULT","evaluation_path")


