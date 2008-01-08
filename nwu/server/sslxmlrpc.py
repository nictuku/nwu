#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006-2008 Yves Junqueira (yves@cetico.org)
#   Copyright (C) 2008 Stephan Peijnik (sp@gnu.org)
#
#    This file is part of NWU.
#
#    NWU is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    NWU is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with NWU.  If not, see <http://www.gnu.org/licenses/>.

import logging

from SecureXMLRPC import SecureXMLRPCServer

# XXX: admin temporarily deactivated
#from nwu_server.rpc_admin import nwu_admin
from nwu_server.db.operation import *
from nwu_server.rpc_agents import *

log = logging.getLogger("nwu_server.db.sslxmlrpc")

def get_refcounts():
    d = {}
    sys.modules
    # collect all classes
    for m in sys.modules.values():
        for sym in dir(m):
            o = getattr (m, sym)
            if type(o) is types.ClassType:
                d[o] = sys.getrefcount (o)
    # sort by refcount
    pairs = map (lambda x: (x[1],x[0]), d.items())
    pairs.sort()
    pairs.reverse()
    return pairs

def top_100():
    for n, c in get_refcounts()[:100]:
        print '%10d %s' % (n, c.__name__)

class SSLServer:
   
    def __init__(self, config):
        self.config = config
        # initialize database
        metadata.bind=config['connection_string']
        setup_all()

    def start(self):
        host = self.config['host']
        port = self.config['port']
        pemfile = self.config['pemfile']
        cacertfile = self.config['cacert']

        log.info("Starting nwu-server. Listening at " + host + ":" + str(port) +\
        ".")
        #nadmin = nwu_admin()
        address = (host, port)
        server = SecureXMLRPCServer(address, pemfile, cacertfile)
        server.register_function(RPC.set_repositories)
        server.register_function(RPC.session_setup)
        server.register_function(RPC.set_list_diff)
        server.register_function(RPC.get_tasks)
        server.register_function(RPC.wipe_this)
        server.register_function(RPC.get_tbl_cksum)
        server.register_function(RPC.add_computer)
        #server.register_function(nadmin.get_info)
        #server.register_function(nadmin.computer_del)
        server.serve_forever()
