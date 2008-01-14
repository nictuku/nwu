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
import logging
# FIXME: all hmac stuff is doomed
import hmac
from elixir import setup_all, create_all, metadata, objectstore
from nwu.server.db.operation import Local
from nwu.server.rpc_agents import RPC
from nwu.server.db.model import metadata, Computer 
from nwu.server.cli import Commands

log = logging.getLogger()
HDLR = logging.StreamHandler()
log.addHandler(HDLR)
log.setLevel(logging.DEBUG)
CONFIG = { 'connection_string' : 'sqlite:///' }
CLI = Commands(config=CONFIG, initialize=False)
PASSWORD = 'foobar'
UNIQ = 'dsadsad1921832918312weee'
TOKEN = hmac.new(PASSWORD, UNIQ).hexdigest()

def setup():
    metadata.bind = CONFIG['connection_string']
    setup_all()
    create_all()
    
class TestServer:

    def test_add_computer(self):

        assert Local.check_token(UNIQ, TOKEN) == False

        # no servers in the database
        zero = Computer.query.count()
        assert zero == 0

        # server doesn't exist yet
        session = RPC.session_setup(UNIQ, TOKEN)
        assert session == False

        m = Computer(hostname='moinmoin', uniq=UNIQ, os_name='Linux', 
            os_version='2.6.x',
            password=PASSWORD)
        objectstore.flush()
        log.debug("Created %s" % repr(m))
        assert Local.check_token(UNIQ, TOKEN) == True
        assert Local.check_token(UNIQ, 'foo') == False
        assert Local.check_token(UNIQ, TOKEN + 'oops') == False

        session = RPC.session_setup(UNIQ, TOKEN)
        assert session == [ UNIQ, TOKEN ] 

class TestServerCli:
    """Makes sure that the 'nwu' CLI commands have the expected effects
    """
    # Important: this class name must be alphabetically after "TestServer"

    def test_install(self):
        # we need objects from the other tests    
        objectstore.flush()
        target_pkgs = ['install_a', 'install_b']
        CLI.cmd_forceinstall(1, *target_pkgs)
        assert RPC.get_tasks([UNIQ, TOKEN]) == [('forceinstall', 
            'install_a install_b')]
        assert CLI.cmd_list() == '1\tmoinmoin\tLinux\n'

