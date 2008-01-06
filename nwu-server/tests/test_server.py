#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006,2007,2008 Yves Junqueira (yves@cetico.org)
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

import sys
sys.path.append('.')
from nwu_server.db.operation import Local
from nwu_server.rpc_agents import RPC
from nwu_server.db.model import *
from nwu_server.cli import Commands
import random
import hmac
import logging

log = logging.getLogger()
hdlr = logging.StreamHandler()
log.addHandler(hdlr)
log.setLevel(logging.DEBUG)
config = { 'connection_string' : 'sqlite:///' }
cli = Commands(config=config, initialize=False)
password='foobar'
uniq='dsadsad1921832918312weee'
token = hmac.new(password, uniq).hexdigest()

def setup():
    metadata.bind=config['connection_string']
    setup_all()
    create_all()
    
class TestServer:

    def test_add_computer(self):

        assert Local.check_token(uniq, token) == False

        # no servers in the database
        zero = Computer.query.count()
        assert zero == 0

        # server doesn't exist yet
        session = RPC.session_setup(uniq, token)
        assert session == False

        m = Computer(hostname='moinmoin', uniq=uniq, os_name='Linux', os_version='2.6.x',
            password=password)
        objectstore.flush()
        log.debug("Created %s" % repr(m))
        assert Local.check_token(uniq, token) == True
        assert Local.check_token(uniq, 'foo') == False
        assert Local.check_token(uniq, token + 'oops') == False

        session = RPC.session_setup(uniq, token)
        assert session == [ uniq, token ] 

class TestServerCli:
    # Important: this class name must be alphabetically after "TestServer"

    def test_install(self):
        # we need objects from the other tests    
        objectstore.flush()
        target_pkgs = ['install_a', 'install_b']
        cli.cmd_forceinstall(1, *target_pkgs)
        assert RPC.get_tasks([uniq, token]) == [('forceinstall', 'install_a install_b')]
        assert cli.cmd_list() == '1\tmoinmoin\tLinux\n'

