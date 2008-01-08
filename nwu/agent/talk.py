#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006-2008 Yves Junqueira (yves@cetico.org)
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

import os
import string
import random
import stat
import ConfigParser

import logging
import sys
import socket

import xmlrpclib

log = logging.getLogger('nwu.agent.misc')

class agent_talk:

    def __init__(self, load_config=True):
        socket.setdefaulttimeout(float(60))
        if load_config:
            self.conffile = '/etc/nwu/agent.conf'
            config = ConfigParser.ConfigParser()
            if not os.access(self.conffile, os.R_OK):
                log.error("Config file " + self.conffile + 
                    " is not readable by the current user.")
                sys.exit(1)
            r = config.read("/etc/nwu/agent.conf")
            self.server_uri = config.get("connection", "server_uri")
            # XXX: check server certificate
            self.rpc = xmlrpclib.Server(self.server_uri)
            self.auth = self._get_auth()

    def _get_auth(self):
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

