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

        query = session.query(TablesVersion).filter_by(tablename=tbl, 
            uniq=comp_uniq)
        a = list(query)
        if len(a) == 0:
            updated = session.save('TablesVersion',tablename=tbl,version=1,uniq=comp_uniq)
            return updated.version
        
        try:
            o = a[0]
            ver = o.version
        except AttributeError:
            updated = session.save('TablesVersion',tablename=tbl,version=1,uniq=comp_uniq)
            return updated.version

        o.version = ver + 1
        return o.version

    def add_computer(password, iuniq, hostname, os_name, os_version):
        """Adds the given computer to the computers database.
        """
        log.info("Creating computer " + iuniq + " " + hostname + " " +\
             os_name + " " + os_version)
        m = session.save('Computer',uniq=iuniq,hostname=hostname, os_name=os_name,
            os_version=os_version,password=password)
        
        return True 

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

    def get_tasks(session):

        (uniq, token) = session

        if not computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"
        hub.begin()
        m = computer.select(computer.q.uniq==uniq)
        ma = list(m)
        q = len(ma)
        if q != 1:
            raise Exception, "Strange. There are more then 1 computer with uniq string =" + uniq

        client_computer = ma[0]

        log.info("Checking pending tasks for " + client_computer.hostname + \
           '(' + str(client_computer.id) + ')'  )
        remote_tasks = []
    #    task._connection.debug = True
        t = task.select(task.q.computerID==client_computer.id)
        ta = list(t)
        qta = len(ta)

        if qta == 0:
            log.info("No pending tasks found for "  + client_computer.hostname + \
           '(' + str(client_computer.id) + ')' )
            return remote_tasks

        for tas in ta:
            if tas.action is None: tas.action = ''
            if tas.details is None: tas.details = ''
        log.info("Task found for "  + client_computer.hostname +  \
             '(' + str(client_computer.id) + '): ' + tas.action + ' ' + tas.details)
        remote_tasks.append((tas.action, tas.details))

        hub.commit()
        hub.end()
        return remote_tasks

    def wipe_this(session, wipe_table):
        (uniq, token) = session

        if not computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        new_map = { 'apt_update_candidates' : 'update_candidates',
            'apt_current_packages' : 'current_packages' }
        # compatibility hack
        # FIXME: future versions of the database know what to do with apt or else
        if wipe_table in new_map.keys():
            wipe_table = new_map[wipe_table]
        if wipe_table not in ['current_packages', 'update_candidates',
                'repositories', 'task']:
                raise Exception, "Illegal table."
                
        hub.begin()
        conn = hub.getConnection()

        m = computer.select(computer.q.uniq==uniq)
        ma = list(m)
        q = len(ma)
        if q != 1:
            raise Exception, "Strange. There are " +  q +  " computer(s) with'" \
            + uniq + "'uniq string and it should have exactly one."

        client_computer = ma[0]

        log.info("Wiping " + wipe_table + " for "   + 
            client_computer.hostname + '(' + \
            str(client_computer.id) + ')' )
        table = eval(wipe_table)
        delquery = conn.sqlrepr(Delete(table.q, where=\
            (table.q.computerID ==  client_computer.id)))

        conn.query(delquery)
        up = update_tbl_version(wipe_table, uniq)
        hub.commit()
        hub.end()
        return up 

    check_token=staticmethod(check_token)
