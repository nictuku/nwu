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
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher 
from nwu_server.rpc_admin import nwu_admin
from nwu_server.db.operation import *
from nwu_server.rpc_agents import *

log = logging.getLogger("nwu_server.db.sslxmlrpc")

class NWURequestHandler(SimpleXMLRPCRequestHandler):
    def finish(self):
        log.debug("Request finished.")
        hub.end_close()

    def do_POST(self):
        """Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to shutdown the socket cleanly.
        Else the connection would just hang. 

        (Thanks to that Python recipe, see below)
        """

        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(0) # Modified here!
            # Using '0' to force a shutdown, or the connection freezes
            # http://www.amk.ca/python/howto/sockets/sockets.html
            

class SSLXMLRPCServer(SocketServer.ThreadingMixIn,
       SSL.SSLServer, SimpleXMLRPCServer):
    def __init__(self, ssl_context, server_uri):
        handler = NWURequestHandler

        # fix suggest in http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496786
        try:
            SimpleXMLRPCDispatcher.__init__(self)
        except TypeError:
            # An exception is raised in Python 2.5 as the prototype of the __init__
            # method has changed and now has 3 arguments (self, allow_none, encoding)
            #
            SimpleXMLRPCDispatcher.__init__(self, False, None)

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
            return 
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                log.error("ERROR: %s, %s" % (request, client_address))
                self.close_request(request)

 
class SSLServer:
    
    def __init__(self,config):
        self.config = config
        self.pemfile = config['pemfile']
        self.ssl_context = self.ctx()

    def ctx(self):
        protocol = 'sslv3'
        ctx = SSL.Context(protocol)
        ctx.set_allow_unknown_ca(1)
        ctx.load_cert(certfile=self.pemfile,
            keyfile=self.pemfile)
#        ctx.load_client_ca('/etc/nwu/cacert.pem')
 #       ctx.load_verify_info('/etc/nwu/cacert.pem')
        ctx.set_verify(SSL.verify_none,10)
    #    ctx.set_session_id_ctx('nwu')
        return ctx

    def start(self):
        host = self.config['host']
        port = self.config['port']
        log.info("Starting nwu-server. Listening at " + host + ":" + str(port) +\
        ".")
        nadmin = nwu_admin()
        ssl_context = self.ctx()
        address = (host, port)
        server = SSLXMLRPCServer(ssl_context, address)
        server.register_function(repositories.set_repositories)
        server.register_function(current_packages.set_current_packages_full)
        server.register_function(computer.session_setup)
        server.register_function(current_packages.set_list_diff)
        server.register_function(get_tasks)
        server.register_function(wipe_this)
        server.register_function(get_tbl_version)
        server.register_function(computer.add_computer)
        server.register_function(nadmin.get_info)
        server.register_function(nadmin.computer_del)
        server.serve_forever()
