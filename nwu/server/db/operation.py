#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006 Yves Junqueira (yves@cetico.org)
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

"""Defines the nwu database scheme, tables and operations.
"""
import sys
import logging
import md5

from nwu.server.db.model import *

class Local:
    @staticmethod
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


