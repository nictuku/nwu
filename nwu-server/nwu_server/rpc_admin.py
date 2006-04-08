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
"""This class is accessed from the RPC interface by administration tools and
provides data and methods for controlling the nwu hosts database.
"""
from md5 import md5
import logging
from db.operation import *
log = logging.getLogger('nwu_server.rpc_admin')

class nwu_admin:
    """RPC methods that control the database using
    local_data.nwu_data
    """

    def __init__(self):
        pass
 
    def get_info(self, auth, info):
        if not self._verify_auth(auth, admin=True):
            raise Exception, "Wrong auth"
        else:
            log.debug("AUTH OK")
        export = []
	
        # This was in __init__, but we must try to avoid caching
        if info == 'computers':
            for mach in computer.select():
                export.append({
                    'id' : mach.id,
                    'uniq' : mach.uniq,
                    'hostname' : mach.hostname,
                    'os_version' : mach.os_version,
                    'os_name' : mach.os_name,
                    })

        elif info == 'tasks':
            for tk in task.select():
                export.append({
                    'id' : tk.id,
                    'computer_id' : tk.computerID,
                    'action' : tk.action,
                    'details' : tk.details,
                    })
     
        return export

    def computer_del(self, computer_id):

        if not self._verify_auth(auth, admin=True):
            raise Exception, "Wrong auth"

        m = computer.select(computer.q.id==computer_id)
        ma = list(m)
        q = len(ma)
        if q == 0:
            raise Exception, "Machine not found in the database."
        if q != 1:
            raise Exception, "There are " +  str(q) +  " computer(s) with'" \
                + uniq + "'uniq string and it should have exactly one."

        client_computer = ma[0]

        log.info("Wiping computer "   + client_computer.hostname + '(' + \
            str(client_computer.id) + ')')

        delquery = conn.sqlrepr(Delete(computer.q, where=\
            (computer.q.id ==  client_computer.id)))

        conn.query(delquery)
        return True 

    def task_append(self, new_task_dict):
        if not self._verify_auth(auth, admin=True):
            raise Exception, "Wrong auth"

        computer_id = new_task['computer_id']
        task_name = new_task['task_name']

        if new_task.has_key('task_detail'):
            task_detail = new_task['task_detail']
        else:
            task_detail = None

        m = computer.select(computer.q.id==computer_id)
        ma = list(m)
        for mach in ma:
            log.debug("Found computer id=" + computer_id + \
            " in the database. Requesting " + task_name + \
            str(task_detail) + ".")

            t = task(computer=computer_id, action=task_name,details=task_detail)

    def _verify_auth(self, auth, admin=True):
        # verify given user against the user database
	# FIXME: is this really safe?

        (username, password) = auth
        u = user.select(user.q.username==username)
        for login in u:
            if not md5(password).hexdigest() == login.password:
                return False
            elif admin == True and login.userlevel == 1:
                return True
            else:
                return True
                        
if __name__ == '__main__':
    na = nwu_admin()
    print na.get_info('computers')
    print na.get_info('tasks')
    na.computer_del(6)
