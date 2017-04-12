Examples
========

Examples of how to start minigenerator and flows are given in this section

## Usage

Minigenerator is well inegrated with mininet and thus very easy to use with it:

```python
from mininet.net import Mininet
from minigenerator.minigen import Minigenerator
from minigenerator.cli import MiniGeneratorCLI

net = Mininet(...)
net.start()

minigen = Minigenerator(net=net)
minigen.start()

MiniGeneratorCLI(minigenerator=minigen,mininet=net)

minigen.stop()
net.stop()
```

See `simple_topo_test.py` for a complete example of how to run minigenerator

## Minigenerator API

Todo


## Custom Functions and Topology

Todo