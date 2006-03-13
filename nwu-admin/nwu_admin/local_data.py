#!/usr/bin/env python
"""Gets nwu nodes data from a local database.
This will be replaced by rpc_data.py sometime.
"""

import sys
# svn test only
sys.path.append('../nwu-server')
from nwu_server.db.operation import *

class nwu_data:

    nodes = []

    def __init__(self):

        m = machine.select()
        ma = list(m)
        print ma
        self.nodes = ma
