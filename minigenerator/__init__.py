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



tmp_path = '/tmp/'
udp_server_address = tmp_path+"flowServer_{0}"
tcp_server_address = tmp_path+"flowServer_tcp_{0}"

