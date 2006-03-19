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


from M2Crypto import SSL
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler


class SSLXMLRPCServer(SSL.SSLServer, SimpleXMLRPCServer):
    def __init__(self, ssl_context, server_uri):
        handler = SimpleXMLRPCRequestHandler
        #    self.handle_error = self._quietErrorHandler
        SSL.SSLServer.__init__(self, server_uri, handler, ssl_context) 
        self.funcs = {}
        self.logRequests = 0
        self.instance = None

class SSLServer:
    
    def __init__(self,pemfile):
        self.pemfile = pemfile
        self.ssl_context = self.ctx()

    def ctx(self):
        ctx = SSL.Context('sslv3')
        ctx.load_cert(self.pemfile)
#        ctx.load_verify_info(pemfile)
        ctx.load_client_ca('/etc/nwu/cacert.pem')
        ctx.load_verify_info('/etc/nwu/cacert.pem')
#        ctx.set_verify(self.verify, self.verify_depth)
#        ctx.set_session_id_ctx('xmlrpcssl')
        #ctx.set_info_callback(verify)
        return ctx

    def start_server(self, host, port):
        ssl_context = self.ctx() 
        address = (host, port)
        server = SSLXMLRPCServer(ssl_context, address)
        return server      
