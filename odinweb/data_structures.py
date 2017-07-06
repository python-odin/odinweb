from collections import namedtuple
from itertools import chain


# Used to define path nodes
PathNode = namedtuple('PathNode', ('name', 'type', 'type_args'))

# Generic definition for a route to an API endpoint
ApiRoute = namedtuple("ApiRoute", ('route_number', 'path', 'methods', 'callback'))
