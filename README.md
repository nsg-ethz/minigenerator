Minigenerator
=============


Set of python tools to generate simple traffic between hosts. Combined with [Mininet](http://mininet.org) network emulator
or ([ipmininet](https://github.com/oliviertilmans/ipmininet),[miniNExT](https://github.com/USC-NSL/miniNExT)). Since all 
those network emulators create network namespaces as hosts, it would be very easy to port to any other namespace based 
emulator.

 
# Installation

Minigenerator depends on Mininet, hence if you do not have it yet get it from the repository:

```bash
sudo apt-get install mininet
```

Or download sourcre code and install natively:

```bash
git clone git://github.com/mininet/mininet.git
mininet/util/install.sh -fnv
```


```bash
git clone https://github.com/nsg-ethz/minigenerator.git 
./install.sh
```

# Features

Minigenerator includes:

 * Enhanced mininet CLI, for example,
 
   `> minigenerator restart all`
 
   Restarts minigenerator in all hosts
    
   `> miningenerator restart h0`
   
   Restarts h0's minigenerator only.
  
 * Json API to send commands to servers running in the hosts
 * Sending and receiving functions can be easily customized (see [examples](https://github.com/nsg-ethz/minigenerator/tree/master/minigenerator/examples)
 * [Unix Socket library for IPC](https://github.com/nsg-ethz/minigenerator/blob/master/minigenerator/misc/unixsockets.py)
 * An [object](https://github.com/nsg-ethz/minigenerator/blob/master/minigenerator/misc/topology.py) that interprets mininet (or subclasses) objects and extracts meaningful topology data which can be accessed later 
   to get topology information. For example:  paths between two nodes, if two nodes are neighbors.



# Examples

At [minigenerator/examples](https://github.com/nsg-ethz/minigenerator/tree/master/minigenerator/examples) you can find 
some examples of how to use the generator given a simple topology created with mininet.