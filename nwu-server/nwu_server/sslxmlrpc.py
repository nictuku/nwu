#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006 Yves Junqueira (yves@cetico.org)
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging
import socket
import SocketServer
from M2Crypto import SSL
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from nwu_server.rpc_admin import nwu_admin
from nwu_server.db.operation import hub

log = logging.getLogger("nwu_server.db.sslxmlrpc")

class NWURequestHandler(SimpleXMLRPCRequestHandler):
    def finish(self):
        log.debug("Request finished.")
        hub.end_close()

class SSLXMLRPCServer(SocketServer.ThreadingMixIn,
       SSL.SSLServer, SimpleXMLRPCServer):
    def __init__(self, ssl_context, server_uri):
        handler = NWURequestHandler
        #    self.handle_error = self._quietErrorHandler
        SSL.SSLServer.__init__(self, server_uri, handler, ssl_context) 
        self.funcs = {}
        self.logRequests = False 
        self.instance = None

    def handle_request(self):
        """Handle one request, possibly blocking."""
        try:
            request, client_address = self.get_request()
        except socket.error, e:
            log.warn("Socket exception: %s" % e)
            return False
        except SSL.SSLError, e:
            log.warn("SSL exception: %s" % e)
            return False
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                log.error("ERROR: %s, %s" % (request, client_address))
                self.close_request(request)

    def start(self):
        host = config['host']
        port = config['port']
        log.info("Starting nwu-server. Listening at " + host + ":" + str(port) +\
        ".")
        nadmin = nwu_admin()
        ssl = sslxmlrpc.SSLServer('/etc/nwu/server.pem')
        server = ssl.start_server(host, port)
        server.register_function(apt_repositories.apt_set_repositories)
        server.register_function(apt_current_packages.apt_set_current_packages_full)
        server.register_function(computer.session_setup)
        server.register_function(apt_current_packages.apt_set_list_diff)
        server.register_function(get_tasks)
        server.register_function(wipe_this)
        server.register_function(get_tbl_version)
        server.register_function(computer.add_computer)
        server.register_function(nadmin.get_info)
        server.register_function(nadmin.computer_del)
        return server
 
class SSLServer:
    
    def __init__(self,pemfile):
        self.pemfile = pemfile
        self.ssl_context = self.ctx()

    def ctx(self):
        protocol = 'sslv23'
        ctx = SSL.Context(protocol)
        ctx.load_cert(self.pemfile)
        ctx.load_client_ca(self.pemfile)
        ctx.load_verify_info(self.pemfile)
        ctx.set_verify(SSL.verify_peer,10)
    #    ctx.set_session_id_ctx('nwu')
        return ctx

    def start_server(self, host, port):
        ssl_context = self.ctx() 
        address = (host, port)
        server = SSLXMLRPCServer(ssl_context, address)
        return server     
