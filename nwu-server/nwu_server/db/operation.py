#!/usr/bin/python
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

"""Defines the nwu database scheme, tables and operations.
"""
import sys
import hmac
import logging
from nwu_server.db.model import *

#cfg = read_conf()

#metadata.bind(cfg.connection_string)

class Local:
    def update_tbl_version(tbl, comp_uniq): 
        """Remember version of clients metadata to enforce data
        syncronization."""

        query = session.query(TablesVersion).filter_by(name=tbl, 
            uniq=comp_uniq)
        a = list(query)
        if len(a) == 0:
            updated = TablesVersion(name=tbl,version=1,uniq=comp_uniq)
            return updated.version
        
        try:
            o = a[0]
            ver = o.version
        except AttributeError:
            updated = TablesVersion(name=tbl,version=1,uniq=comp_uniq)
            return updated.version

        o.version = ver + 1
        return o.version

    def check_token(uniq, token):
        """Checks if the specified token was generated using the stored
        computer password.
        """
        check_t = Computer.get_by(uniq=uniq)

        password = ''

        if not check_t:
            # No computer with that specified uniq id was found.
            log.debug("No computer with that uniq found")
            return False
        else:
            password = check_t.password

        valid_token = hmac.new(password, uniq).hexdigest()

        if valid_token == token:
            # Yeah, this is a valid token!
            return True
        else:
            log.debug("Invalid token specified")
            return False

    check_token=staticmethod(check_token)
    update_tbl_version=staticmethod(update_tbl_version)

