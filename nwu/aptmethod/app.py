#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from nwu.common.app import Application, Command
from nwu.common.aptmethod import AptMethod
from nwu.common.rpc import Proxy

__author__ = 'Stephan Peijnik'
__version__ = '0.1'

class NWUAptMethod(AptMethod):
    def __init__(self, app):
        self.app = app
        self.proxy = app.proxy
        AptMethod.__init__(self, __version__)
        
    def handle_600(self, msg_string, headers):
        uri = headers['URI']
        filename = headers['Filename']
        idx = self.convert_truefalse(headers['Index-File'])

        if idx:
            self.get_index_file(uri, filename)
        else:
            self.get_file(uri, filename)

    def get_index_file(self, uri, filename):
        # TODO: implement index file retrieval (needs some work on the server
        # code first)
        pass

    def get_file(self, uri, filename):
        # TODO: implement file retrieval (needs some work on the server
        # code first).
        pass

class AptMethodRootCommand(Command):
    def execute(self, app, args, cmdName=None):
        app.configPath = app.DEFAULT_CONFIG_PATH
        app.read_config()

        app.init_connection()

class AptMethodApp(Application):
    DEFAULT_CONFIG = '/etc/nwu/agent.conf'
    DEFAULT_CA_CERT = '/etc/nwu/ca.cert'
    DEFAULT_AGENT_CERT = '/etc/nwu/agent.crt'
    DEFAULT_AGENT_KEY = '/etc/nwu/agent.key'
    DEFAULT_SERVER_URI = 'https://localhost:8088'

    def __init__(self, args=sys.argv[1:], binName=sys.argv[0]):
        Application.__init__(self, args, binName)
        self.server_uri = None
        self.ca_cert = None
        self.agent_cert = None
        self.agent_key = None

    def init_connection(self):
        self.apt_method = NWUAptMethod(self)

        self.server_uri = self.config.get(
            'connection', 'server_uri', AptMethodApp.DEFAULT_SERVER_URI)
        self.ca_cert = self.config.get(
            'crypto', 'cacert', AptMethodApp.DEFAULT_CA_CERT)
        self.agent_cert = self.config.get(
            'crypto', 'agentcert', AptMethodApp.DEFAULT_AGENT_CERT)
        self.agent_key = self.config.get(
            'crypto', 'agentkey', AptMethodApp.DEFAULT_AGENT_KEY)
                                              
                                          
        self.proxy = Proxy(self.server_uri, key_file=self.agent_key,
                           cert_file=self.agent_cert, 
                           ca_cert_file=self.ca_cert)
        
