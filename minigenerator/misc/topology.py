import json
from ipaddress import ip_interface
from minigenerator.logger import log
from minigenerator.misc import InvalidIP, HostDoesNotExist
import networkx as nx
import copy

class TopologyDB(object):
    """A convenience store for auto-allocated mininet properties.
    This is *NOT* to be used as IGP graph for a controller application,
    use the graphs reported by the southbound controller instead.
    
    Based on Olivie Tilmans TopologyDB from fibbing project:
    https://github.com/Fibbing/FibbingNode/blob/master/fibbingnode/misc/mininetlib/ipnet.py
    """
    def __init__(self, db=None, net=None, *args, **kwargs):
        super(TopologyDB, self).__init__(*args, **kwargs)
        """
        dict keyed by node name ->
            dict keyed by - properties -> val
                          - neighbor   -> interface properties
        """
        self._network = {}

        if net:
            self.parse_net(net)

        elif db:
            self.load(db)

        else:
            log.warning('Topology instantiated without any data')

    def load(self, fpath):
        """Load a topology database from the given filename"""
        with open(fpath, 'r') as f:
            self._network = json.load(f)

    def save(self, fpath):
        """Save the topology database to the given filename"""
        with open(fpath, 'w') as f:
            json.dump(self._network, f)

    def _node(self, x):
        try:
            return self._network[x]
        except KeyError:
            raise ValueError('No node named %s in the network' % x)

    def __getitem__(self, item):

        return self._node(item)

    def _interface(self, x, y):
        return self._network[x][y]

    def interface(self, x, y):
        """Return the ip_interface for node x facing node y"""
        return ip_interface(self._interface(x, y)['ip'])

    def interface_bandwidth(self, x, y):
        """Return the bandwidth capacity of the interface on node x
        facing node y. If it is unlimited, return -1"""
        return self._interface(x, y)['bw']

    def subnet(self, x, y):
        """Return the subnet linking node x and y"""
        return self.interface(x, y).network.with_prefixlen

    def setRouterId(self, x):
        """Return the OSPF router id for node named x"""
        router = self._network[x]
        if router['type'] != 'router':
            raise TypeError('%s is not a router' % x)

        return router.get('routerid')

    def getRouterId(self,x):

        router = self._network[x]
        if router['type'] != 'router':
            raise TypeError('%s is not a router' % x)

        return router['routerid']

    def interfaceIP(self,node,interface):

        """
        Returns the interface IP of a routers
        :param router:
        :param switch:
        :return:
        """
        connected_to = self._network[node]["interfaces_to_node"][interface]
        return self._interface(node,connected_to)['ip'].split("/")[0]


    def type(self,node):

        return self._network[node]['type']

    @staticmethod
    def otherIntf(intf):
        """Get the interface on the other of a link"""
        l = intf.link
        return (l.intf1 if l.intf2 == intf else l.intf2) if l else None


    def parse_net(self, net):
        """Stores the content of the given network"""
        for h in net.hosts:
            self.add_host(h)
        for s in net.switches:
            self.add_switch(s)
        if hasattr(net,"routers"):
            for r in net.routers:
                self.add_router(r)
        for c in net.controllers:
            self.add_controller(c)

    def _add_node(self, n, props):
        """Register a network node"""

        interfaces_to_nodes = {}

        for itf in n.intfList():
            nh = TopologyDB.otherIntf(itf)
            if not nh:
                continue  # Skip loopback and the likes

            props[nh.node.name] = {
                'ip': '%s/%s' % (itf.ip, itf.prefixLen),
                'mac' : '%s' % (itf.mac),
                'intf': itf.name,
                'bw': itf.params.get('bw', -1)
            }
            interfaces_to_nodes[itf.name] = nh.node.name
        #add an interface to node mapping that can be useful
        props['interfaces_to_node'] = interfaces_to_nodes
        self._network[n.name] = props

    def add_host(self, n):
        """Register an host"""
        attributes = {'type': 'host'}
        #n.gateway attribute only exists in my custom mininet
        if hasattr(n,"gateway"):
            attributes.update({'gateway':n.gateway})
        elif 'defaultRoute' in n.params:
            attributes.update({'gateway':n.params['defaultRoute']})
        self._add_node(n, attributes)

    def add_controller(self, n):
        """Register an controller"""
        self._add_node(n, {'type': 'controller'})

    def add_switch(self, n):
        """Register an switch"""
        self._add_node(n, {'type': 'switch'})

    def add_router(self, n):
        """Register an router"""
        self._add_node(n, {'type': 'router',
                           'routerid': n.id})
        #we overrite the router id using our own function.
        self._network[n.name]["routerid"] = self.setRouterId(n.name)


class NetworkGraph(object):
    def __init__(self, topologyDB):

        self.topologyDB = topologyDB

        self.graph = self.loadGraphFromDB(self.topologyDB)

    def loadGraphFromDB(self, topologyDB):

        g = nx.Graph()

        for node, interfaces in topologyDB.original_network.items():
            if node not in g.nodes() and (node not in ["default_controller", "sw-mon", "ryu_controller"]):
                g.add_node(node)
                g.node[node]['type'] = topologyDB.type(node)

                # TODO IMPORTANT, here we will differenciate a type of routers. The ones that contain the letter e, will be
                # classified as edge routers. Edge routers are used to compute all the possible paths within the
                # topology
                if 'e' in node:
                    g.node[node]['edge'] = True

                elif "a" in node:
                    g.node[node]['aggregation'] = True

                for intf in interfaces:
                    # we should ignore routerid, type.
                    # TODO have to find a better way to do this
                    if intf in ["routerid", 'type', 'gateway']:
                        continue

                    # else itf its a real interface so we add an edge,
                    # only if the connected node has been created.
                    connectedTo = topologyDB._interface(node, intf)["connectedTo"]
                    if connectedTo in g.nodes():
                        # add edge
                        g.add_edge(node, connectedTo)
        return g

    def addEdge(self, node1, node2):

        if node1 in self.graph.node and node2 in self.graph.node:
            self.graph.add_edge(node1, node2)

    def addNode(self, node):

        self.graph.add_node(node)
        self.graph.node[node]['type'] = self.topologyDB.original_network[node]["type"]
        if 'e' in node:
            self.graph.node[node]['edge'] = True

        elif "a" in node:
            self.graph.node[node]['aggregation'] = True

        for neighbor_node in self.topologyDB.original_network_node_to_node[node]:

            if neighbor_node in self.graph.node:
                # add edge
                self.graph.add_edge(node, neighbor_node)

    def removeEdge(self, node1, node2):

        self.graph.remove_edge(node1, node2)

    def removeNode(self, node):

        self.graph.remove_node(node)

    def keepOnlyRouters(self):

        to_keep = [x for x in self.graph.node if self.graph.node[x]['type'] == 'router']

        return self.graph.subgraph(to_keep)

    def keepRoutersAndNormalSwitches(self):

        to_keep = [x for x in self.graph.node if self.graph.node[x]['type'] == 'router'] + self.getNormalSwitches()

        return self.graph.subgraph(to_keep)

    def getNormalSwitches(self):

        return [x for x in self.graph.node if "sw" in x]

    def getOVSSwitches(self):

        return [x for x in self.graph.node if "ovs" in x]

    def setNodeShape(self, node, shape):

        self.graph.node[node]['node_shape'] = shape

    def setNodeColor(self, node, color):

        self.graph.node[node]['node_color'] = color

    def setNodeTypeShape(self, type, shape):

        for node in self.graph.node:
            if self.graph.node[node]['type'] == type:
                self.setNodeShape(node, shape)

    def setNodeTypeColor(self, type, color):

        for node in self.graph.node:
            if self.graph.node[node]['type'] == type:
                self.setNodeColor(node, color)

    def getFatTreePositions(self, k=4, normalSwitches=True):

        # assume that g is already the reduced graph
        # assume that we named the nodes using the fat tree "structure"
        # assume that we know k

        positions = {}

        normalSwitchStartPos = (1, 0)
        edgeStartPos = (1, 1)
        aggStartPos = (1, 2)

        normalSwitchBaseName = "sw_{0}_{1}"
        edgeBaseName = "r_{0}_e{1}"
        aggBaseName = "r_{0}_a{1}"
        coreBaseName = "r_c{0}"

        if normalSwitches:
            # allocate switches
            for pod in range(k):
                for sub_pod in range(k / 2):
                    positions[normalSwitchBaseName.format(pod, sub_pod)] = normalSwitchStartPos
                    normalSwitchStartPos = (normalSwitchStartPos[0] + 3, normalSwitchStartPos[1])
                normalSwitchStartPos = (normalSwitchStartPos[0] + 2.5, normalSwitchStartPos[1])

        # allocate edge routers
        for pod in range(k):
            for sub_pod in range(k / 2):
                positions[edgeBaseName.format(pod, sub_pod)] = edgeStartPos
                edgeStartPos = (edgeStartPos[0] + 3, edgeStartPos[1])
            edgeStartPos = (edgeStartPos[0] + 2.5, edgeStartPos[1])

        # allocate aggregation routers
        for pod in range(k):
            for sub_pod in range(k / 2):
                positions[aggBaseName.format(pod, sub_pod)] = aggStartPos
                aggStartPos = (aggStartPos[0] + 3, aggStartPos[1])
            aggStartPos = (aggStartPos[0] + 2.5, aggStartPos[1])

        totalDistance = positions[edgeBaseName.format(k - 1, (k / 2) - 1)][0] - 1
        print totalDistance
        step = totalDistance / float(((k / 2) ** 2))
        print step
        coreStartPos = (1 + step / 2, 3.5)

        # allocate core routers
        for pod in range((k / 2) ** 2):
            positions[coreBaseName.format(pod)] = (coreStartPos[0], coreStartPos[1])
            coreStartPos = (coreStartPos[0] + step, coreStartPos[1])

        print positions
        return positions

    def setEdgeWeights(self, link_loads={}):

        pass

    def getHosts(self):

        return [x for x in self.graph.node if self.graph.node[x]['type'] == 'host']

    def getEdgeRouters(self):

        return [x for x in self.graph.node if "edge" in self.graph.node[x]]

    def getAggRouters(self):

        return [x for x in self.graph.node if "aggregation" in self.graph.node[x]]

    def getRouters(self):

        return [x for x in self.graph.node if self.graph.node[x]["type"] == "router"]

    def areNeighbors(self, n1, n2):

        return n1 in self.graph.adj[n2]

    def getNeighbors(self, node):

        return self.graph.adj[node].keys()

    def getGatewayRouter(self, host):

        # So here we make the assumption that host: h_0_0 its always connected to ovs_0_0 switch.
        # Therefore, we will start from there. From ovs_x_y, two scenarios can happen. First, the switch is connected
        # to another switch named s_x_y, or is connected to an edge router.

        if not (self.graph.has_node(host)):
            # replace that for a debug...
            print "Host %s does not exist" % host
            return None

        x = host.split("_")[1]
        y = host.split("_")[2]
        ovs_switch = "ovs_%s_%s" % (x, y)

        ovs_adjacent_nodes = self.graph.adj[ovs_switch].keys()

        # now i try to get the router or the switch
        for node in ovs_adjacent_nodes:
            node_type = self.graph.node[node]['type']
            if node_type == "switch":

                # we are in the second switch
                sw_adjacent_nodes = self.graph.adj[node].keys()
                for node2 in sw_adjacent_nodes:
                    if self.graph.node[node2]['type'] == "router":
                        return node2

            elif node_type == "router":
                return node
        # gateway was not found
        return None

    def getHostsBehindRouter(self, router):

        # Returns all the hosts that have router as a gateway.
        # !!! IMPORTANT: We make the assumption that the topology used here is a fat tree
        # and that the edge router can face a switch or ovs switches

        hosts = []

        if not (self.graph.has_node(router)):
            # replace that for a debug...
            print "Host %s does not exist" % router
            return None

        router_neighbors = self.graph.neighbors(router)

        # if the router is connected to a normal switch
        if any("sw" in x for x in router_neighbors):

            # we get swtich neighbors and in theory we should find ovs switches
            # we assume that there is only one switch touching that router
            for node in router_neighbors:
                if self.graph.node[node]['type'] == 'switch':
                    sw = node
            switch_neighbors = self.graph.neighbors(sw)

            for switch in switch_neighbors:
                # if its an ovs switch
                if self.graph.node[switch]['type'] == 'switch':
                    hosts.append(switch.replace("ovs", "h"))

        # we go over the ovs switches to find the hosts
        elif any("ovs" in x for x in router_neighbors):

            for switch in router_neighbors:
                # if its an ovs switch
                if self.graph.node[switch]['type'] == 'switch':
                    hosts.append(switch.replace("ovs", "h"))

        # the edge router has no switches next to it.
        else:
            return None

        return hosts

    def numberofPathsBetweenEdges(self):

        total_paths = 0
        edgeRouters = self.getEdgeRouters()
        for router in edgeRouters:
            for router_pair in edgeRouters:
                if router == router_pair:
                    continue
                npaths = sum(1 for _ in nx.all_shortest_paths(self.graph, router, router_pair))
                total_paths += npaths
        return total_paths

    def getAllPaths(self):

        paths = []
        edgeRouters = self.getEdgeRouters()
        for router in edgeRouters:
            for router_pair in edgeRouters:
                if router != router_pair:
                    paths += list(nx.all_shortest_paths(self.graph, router, router_pair))
        return paths

    def totalNumberOfPaths(self):

        """
        This function is very useful if the topology is unknown, however if we are using a fat tree, the number of paths is more or less
        (k/2**2) = number of paths from one node to another node that its not in the same pod
        number of nodes its k**3 / 4
        so number of paths is : (k/2**2) * (k**3)/4 - k**2/4)(this is number of nodes outside the pod) * total number of nodes
        here we should add the number of paths inside the pod
        + number of paths between hosts connected by the same router.
        :return:
        """

        total_paths = 0
        for host in self.getHosts():
            for host_pair in self.getHosts():
                if host == host_pair:
                    continue

                # compute the number of paths
                npaths = sum(1 for _ in nx.all_shortest_paths(self.graph, host, host_pair))
                total_paths += npaths

        return total_paths

    def getPathsBetweenHosts(self, srcHost, dstHost):

        """
        compute the paths between two hosts
        :param srcHost:
        :param dstHost:
        :return:
        """

        # first we get the gateways
        srcEdge = self.getGatewayRouter(srcHost)
        dstEdge = self.getGatewayRouter(dstHost)

        paths = nx.all_shortest_paths(self.graph, srcEdge, dstEdge)
        paths = [tuple(x) for x in paths]

        return paths

    def inSameSubnet(self, srcHost, dstHost):

        """
        Function to check if two hosts belong to the same subnetwork, in that case they do not use external paths
        so flows that do not live a the subnetwork can not be loadbalanced.

        To check if they belong to the same subnetwork ,since we do not store
        :param srcHost:
        :param dstHost:
        :return:
        """

        return self.getGatewayRouter(srcHost) == self.getGatewayRouter(dstHost)

    # returns all the edges between routers in the network
    def getEdgesBetweenRouters(self):

        allEdges = self.graph.to_directed().edges(nbunch=self.getRouters())

        # filter the edges and remove the ones that have switches connected
        return [x for x in allEdges if not (any("sw" in s for s in x) or any("ovs" in s for s in x))]


class Topology(TopologyDB):
    def __init__(self, loadNetworkGraph=True,hostsMappings=True, *args, **kwargs):

        super(Topology, self).__init__(*args, **kwargs)

        # save network startup state
        # in case of link removal we use this objects to remember the state of links and nodes before removal
        # this assumes that the topology will not be enhanced, meaning that links and nodes can be removed and added, but
        # new links or devices can not bee added.

        self.original_network = copy.deepcopy(self._network)

        # if loadNetworkGraph:
        #     self.networkGraph = NetworkGraph(self)

        #loads hosts to ip and ip to hosts mappings
        self.hostsIpMapping = {}
        if hostsMappings:
            self.hostsIpMappings()


    def hostsIpMappings(self):

        """
        Creates a mapping between host names and ip and viceversa
        :return:
        """

        self.hostsIpMapping = {}
        hosts = self.getHosts()
        self.hostsIpMapping["ipToName"] = {}
        self.hostsIpMapping["nameToIp"] = {}
        for host in hosts:
            ip = self.interfaceIP(host,"{0}-eth0".format(host))
            self.hostsIpMapping["ipToName"][ip] = host
            self.hostsIpMapping["nameToIp"][host] = ip

    def getHostName(self, ip):

        """
        Returns the host name of the host that has the ip address
        :param ip:
        :return:
        """
        name = self.hostsIpMapping.get("ipToName").get(ip)
        if name:
            return name
        raise InvalidIP("Any host of the network has the ip {0}".format(ip))

    def getHostIp(self, name):

        """
        returns the ip of host name
        :param name:
        :return:
        """

        ip = self.hostsIpMapping.get("nameToIp").get(name)
        if ip:
            return ip
        raise HostDoesNotExist("Any host of the network has the name {0}".format(name))


    def getNeighbors(self, node):

        return self.networkGraph.getNeighbors(node)


    def getMappingInterfacesFacingHost(self, src):
        # we use the special dictionary network_node_to_node where dictionary keys are neighbor nodes instead of
        # interfaces

        self.aggregationRouters = {}
        self.coreRouters = {}

        self.aggregationRoutersReverse = {}
        self.coreRoutersReverse = {}

        gatewayRouter = self.getGatewayRouter(src)

        # first we find the aggregation routers
        for router in self._network_node_to_node[gatewayRouter].iterkeys():

            if router in {"routerid", "type"}:
                continue

            elif "_a" in router:
                self.aggregationRouters[self._network_node_to_node[router][gatewayRouter]["ip"].split("/")[0]] = router
                self.aggregationRoutersReverse[router] = \
                self._network_node_to_node[router][gatewayRouter]["ip"].split("/")[0]

        for aggRouter in self.aggregationRouters.itervalues():
            for coreRouter in self._network_node_to_node[aggRouter].iterkeys():
                if coreRouter in {"routerid", "type"}:
                    continue

                elif "_c" in coreRouter:
                    self.coreRouters[self._network_node_to_node[coreRouter][aggRouter]["ip"].split("/")[0]] = coreRouter
                    self.coreRoutersReverse[coreRouter] = \
                    self._network_node_to_node[coreRouter][aggRouter]["ip"].split("/")[0]


    def areNeighbors(self, n1, n2):

        return self.networkGraph.areNeighbors(n1, n2)

    def inSameSubnetwork(self, srcHost, dstHost):

        """
        Checks if src host and dst host belong to the same subnet.
        The function assumes that every host has only one interface
        :param srcHost:
        :param dstHost:
        :return: Returns a boolean
        """

        # srcIp = self.network[srcHost]["{0}-eth0".format(srcHost)]["ip"]
        # dstIp = self.network[dstHost]["{0}-eth0".format(dstHost)]["ip"]

        if srcHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(srcHost))

        if dstHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(dstHost))

        return self.getGatewayRouter(srcHost) == self.getGatewayRouter(dstHost)
        # return ip_interface(srcIp).network == ip_interface(dstIp).network

    def getPathsBetweenHosts(self, srcHost, dstHost):

        """
        Returns all the possible paths with same cost between two hosts
        :param srcHost:
        :param dstHost:
        :return:
        """

        if srcHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(srcHost))

        if dstHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(dstHost))

        return self.networkGraph.getPathsBetweenHosts(srcHost, dstHost)

    # also works for aggregation routers used in short paths edge->agg->edge
    def coreToPath(self, src, dst, coreRouter):
        # src and dst are names

        paths = self.getPathsBetweenHosts(src, dst)

        for path in paths:
            if coreRouter in path:
                return path

        return []

    # DEBUG FUNCTION CREATED TO TEST HOW BAD WAS THE LINK FAILURE
    def coresConnectedToAggregation(self, aggRouter):
        # from an aggregation router it returns all the core routers connected to it

        return [x for x in self.networkGraph.graph.adj[aggRouter].keys() if "c" in x]

    def getGatewayRouter(self, host):

        """
        Given a host it returns its gateway router
        :param host:
        :return:
        """

        if host not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(host))

        #TODO: not all hosts have gateways
        return self._network[host]["gateway"]

    def totalNumberOfPaths(self):

        """
        Returns the total number of paths between every host. This function is not really used, instead
        numberOfPathsBetweenEdges should be used.
        :return:
        """

        return self.networkGraph.totalNumberOfPaths()

    def getHostsBehindRouter(self, router):

        """
        Returns a list with all the hosts that have router as a gateway
        :param router:
        :return:
        """

        if router not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(router))

        return self.networkGraph.getHostsBehindRouter(router)

    def getHostsInOtherSubnetworks(self, host):

        """
        Returns all the hosts from other subnetworks. This is used to generate traffic only to "remote" hosts
        :param host:
        :return:
        """

        if host not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(host))

        # returns all the hosts that are in other subnetworks
        gatewayEdgeRouter = self.getGatewayRouter(host)
        edgeRouters = self.getEdgeRouters()

        otherHosts = []
        for edgeRouter in edgeRouters:
            if edgeRouter == gatewayEdgeRouter:
                continue
            otherHosts += self.getHostsBehindRouter(edgeRouter)

        return otherHosts

    def getHostsInOtherPods(self, host):

        # all hosts
        allHosts = set(self.getHosts().keys())

        # hosts in subnetwork
        hosts_in_subnetwork = set(self.getHostsBehindRouter(self.getGatewayRouter(host)))

        # hosts in the pod but not in the subnetwork
        hosts_in_the_pod = set(self.getHostsInSamePod(host))

        allHosts -= hosts_in_subnetwork
        allHosts -= hosts_in_the_pod

        return list(allHosts)

    def sortHostsByName(self, hostsList):

        pseudoList = [(hostName, int(hostName.split("_")[1]), int(hostName.split("_")[2])) for hostName in hostsList]

        pseudoList = sorted(pseudoList, key=lambda host: (host[1], host[2]))

        return [x[0] for x in pseudoList]

    def getHostsInSamePod(self, host):

        # returns the name of all the hosts that are in the same pod but different subnetworks

        if host not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(host))

        edgeRouters = self.getEdgeRouters()
        current_host_edge = self.getGatewayRouter(host)

        # filter and keep only edges with same pod number
        edgeInPod = [router for router in edgeRouters if
                     router.split("_")[1] == current_host_edge.split("_")[1] and router != current_host_edge]

        hosts = []
        for edgeRouter in edgeInPod:
            hosts += self.getHostsBehindRouter(edgeRouter)

        return hosts

    def numberOfPathsBetweenEdges(self):

        """
        Return the number of paths between edge routers. In theory the returned number is the total paths we have to
        find in order to fill our header database
        :return:
        """

        return self.networkGraph.numberofPathsBetweenEdges()

    def numberDevicesInPath(self, src, dst):
        # returns the number of devices between two nodes in the network

        if src not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(src))

        if dst not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(dst))

        return len(nx.shortest_path(self.networkGraph.graph, src, dst))

    def getHopsBetweenHosts(self, src, dst):

        if src not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(src))

        if dst not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(dst))

        return self.numberDevicesInPath(self.getGatewayRouter(src),
                                        self.getGatewayRouter(dst))

    # used at the traceroute SERVEr to know the number of hops between two hosts..
    def loadHostsPositionsRelativeToASource(self, src):

        """
        Loads hosts positions relative to a source. It stores the names of hosts that are in the same subnetwork,
        same pod or in another pod
        :param src:
        :return:
        """

        if src not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(src))

        # save relative source
        self.hosts_in_src = src
        self.hosts_in_same_pod = set(self.getHostsInSamePod(src))
        self.hosts_in_other_pod = set(self.getHostsInOtherPods(src))

    #########################################################################################
    # THIS FUNCTION ONLY WORK IF loadHostsPositionsRelativeToASource has been called before


    def getHopsToCore(self, srcHost, dstHost):
        """
        Gets the distance to the core router in a Fat tree topology. For inter-pod communications
        the distance is always 3 hops, for intra-pod communication 2
        :param src:
        :param dst:
        :return:
        """
        if srcHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(srcHost))

        if dstHost not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(dstHost))

        if self.inSameSubnetwork(srcHost, dstHost):
            return 0

        elif dstHost in self.hosts_in_same_pod:
            return 2

        elif dstHost in self.hosts_in_other_pod:
            return 3

        else:
            # should never happen
            return -1

    def getRouters(self):

        "Gets the routers from the topologyDB"

        return {node: self._network[node] for node in self._network if self._network[node]["type"] == "router"}

    def getEdgeRouters(self):

        return self.networkGraph.getEdgeRouters()

    def getHosts(self):

        "Gets the routers from the topologyDB"

        return {node: self._network[node] for node in self._network if self._network[node]["type"] == "host"}

    def getSwitches(self):

        return {node: self._network[node] for node in self._network if self._network[node]["type"] == "switch"}

    def isOVS(self, node):

        if node not in self._network:
            raise HostDoesNotExist("{0} does not exist".format(node))

        return self._network[node]["type"] == "switch" and node[:3] == "ovs"



class FatTree(Topology):

    """
    Fat tree topology functionalities: Assumes that naming as follows: 
    hosts: h_podnum_number -> h_0_0
    edge sw/router: s/r_podnum_e(number) -> s/r_0_e0
    aggregation sw/router: s/r_podnum_a(number) -> s/r_0_a0
    core sw/router s/r_c(number) -> r_c0/s_c0
    """

    def __init__(self):
        pass

    def getPod(self, name):

        return name.split("_")[1]
