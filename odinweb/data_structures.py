from collections import namedtuple


# Used to define path nodes
PathNode = namedtuple('PathNode', ('name', 'type', 'type_args'))

# Generic definition for a route to an API endpoint
ApiRoute = namedtuple("ApiRoute", ('path', 'methods', 'callback'))
