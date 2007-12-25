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

import os
import string
import random
import stat
import ConfigParser
from M2Crypto import SSL
from M2Crypto.m2xmlrpclib import Server, SSL_Transport

import logging
import sys
import socket

log = logging.getLogger('nwu_agent.misc')

class agent_talk:
    #pemfile='/etc/nwu/client.pem'
    debug=False

    def __init__(self, load_config=True):
        #socket.setdefaulttimeout(float(100))
        if load_config:
            self.conffile = '/etc/nwu/agent.conf'
            config = ConfigParser.ConfigParser()
            if not os.access(self.conffile, os.R_OK):
                log.error("Config file " + self.conffile + 
                    " is not readable by the current user.")
                sys.exit(1)
            r = config.read("/etc/nwu/agent.conf")
            self.server_uri = config.get("connection", "server_uri")
            self.rpc = self.XClient(self.server_uri)

    def _my_ctx(self):
        protocol = 'sslv3'
        ctx = SSL.Context(protocol)
        ctx.set_allow_unknown_ca(True)
        # Currently, none of this would work.
        # Leaving it like this, it will still check if the
        # certificate name matches the host address 

#        ctx.load_cert(self.pemfile)
#        ctx.load_client_ca('/etc/nwu/cacert.pem')
#        ctx.load_verify_info('/etc/nwu/cacert.pem')
        #ctx.set_verify(SSL.verify_peer|SSL.verify_fail_if_no_peer_cert,10)
        #ctx.set_verify(SSL.verify_,10)
        #ctx.set_verify(SSL.verify_none,10)
        #ctx.set_session_id_ctx('nwu')
        return ctx

    def XClient(self, server_uri):
        ctx = self._my_ctx()
        transport = SSL_Transport(ctx) 
        # Python 2.5 fix
        transport._use_datetime = False
        xs = Server(server_uri, transport, verbose=self.debug)
        return xs

    def get_auth(self):
        auth_path = "/var/spool/nwu/auth"
        try:
            st = os.stat(auth_path)
        except:
            pass
        else:
            mode = st[stat.ST_MODE]
            if mode != 33216 and mode != 33152: # 600 and 700
                raise Exception, "Wrong permission for the auth file (" +\
                  auth_path + "). See the README file."
        r = os.umask(0177)
        auth_file = ConfigParser.ConfigParser()
        # FIXME: create new file if needed
        r = auth_file.read(auth_path)
        changed = False
        if not auth_file.has_section('auth'):
            auth_file.add_section('auth')
            changed = True
        if not auth_file.has_option('auth', 'uniq') or \
            len(auth_file.get("auth", "uniq")) != 32:
            # No or bad uniq string found in the auth file. Creating a new one.
            letters = string.ascii_uppercase + string.digits
            uniq = ''
            for i in range(32):
                uniq += random.choice(letters)
            auth_file.set("auth", "uniq", uniq)
            changed = True
        else:
            uniq = auth_file.get("auth", "uniq")
        # Checking for password. If it doesn't find one, generate
        # a new random string.
        # FIXME: Security issue: is variable length password creation
        # a good idea? 
        # FIXME: Security issue: should the server create a password instead?
        if not auth_file.has_option('auth', 'password') or \
            len(auth_file.get("auth", "password")) != 255:
           # Creating a new password string of 255 bytes.
            password = ''
            letters = string.ascii_letters + string.digits
            for i in range(255):
                password += random.choice(letters)
            auth_file.set("auth", "password", password)
            changed = True
        else:
            password = auth_file.get("auth", "password")
        # dump changes
        if changed:
            log.info("Storing auth settings to %s" % auth_path)
            auth_fd = open(auth_path, 'w')
            auth_file.write(auth_fd)
            auth_fd.close()
        session = uniq, password
        return session

