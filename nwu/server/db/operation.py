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
import md5

from nwu.server.db.model import *

class Local:
    def update_tbl_version(tbl, comp_uniq): 
        """Remember version of clients metadata to enforce data
        syncronization."""
        try:
            new_tbl = new_map[tbl]
        except: 
            raise Exception, "Illegal table: %s" % tbl

        mytable = eval(new_tbl)
        # we need fresh information
        objectstore.flush()
        client_computer = Computer.get_by(uniq=comp_uniq)
        try:
            query = mytable.query.filter_by(computer=client_computer).order_by(mytable.c.name)
        except:
            # FIXME: use "has_options" in the model to avoid this
            # "Tasks" has no 'name' columns
            query = mytable.query.filter_by(computer=client_computer)
        data = ''
        for info in query.all():
            data += info.name + '+' + info.version + ' '
        cksum = md5.new(data).hexdigest()
        
        delitems = TablesVersion.query.filter_by(name=tbl,uniq=comp_uniq).all()
        for item in delitems:
            session.delete(item)
        updated = TablesVersion(name=tbl,version=cksum,uniq=comp_uniq)
        return updated.version

    def check_token(uniq, token):
        """Checks if the specified token was generated using the stored
        computer password.
        """
        check_t = Computer.get_by(uniq=uniq)

        if not check_t:
            # No computer with that specified uniq id was found.
            log.debug("check_token: no computer with that uniq found")
            return False
        else:
            # XXX: being replaced by x509 authentication
            return True 

    check_token=staticmethod(check_token)
    update_tbl_version=staticmethod(update_tbl_version)

