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
from nwu.server.db.model import Computer, Tasks, UpdateCandidates
from nwu.server.db.model import db_bind
from elixir import session, metadata, setup_all 

from nwu.common.config import Config

VERSION = '0.1.7'

def show_help():
    print \
    """Usage: nwu <command> <options> [arguments]
    Command line manager for NWU, version """ + VERSION + """.

    Available commands:

  addrep  <computer> <repository uri>  : Add new repository
  adduser <name> <level:0|1>     : Add a new user, admin or not
  forceinstall <computer> <packages>  : Install defined packages in the computer (force)
  help                           : This help message
  install <computer> <packages>  : Install defined packages in the computer
  list    [group]                : Lists all computers or specified group
  update <computer>             : Update packages list
  upgrade <computer>             : Upgrade all packages in the computer
  view    <computer> <info>      : View computer informations

    Available groups for list command:

        outdated
    """
    sys.exit(64)

class Commands():
    commands = {
    "forceinstall" : "<computer> <packages>  : Install defined packages in the\
 computer (force)",
    "install" : "<computer> <packages>  : Install defined packages in the\
 computer",
    "help" : "                          : This help message",
    "upgrade" : "<computer>             : Upgrade all packages in the\
 computer",
    "update"  : "<computer>             : Update packages list",
    "list" : "   [group]                : Lists all computers or specified\
 group",
    "view" : "   <computer> <info>      : View computer informations",
    "addrep" : " <computer> <repository uri>  : Add new repository",
        
    }

    def __init__(self, config=None, initialize=True):
        # FIXME: remove this 'initialize' check
        # it's used the tests, but I could simply override the class instead
        if initialize:
            if not config:
                config = Config()
            # FIXME: use nwu.server.app instead when it's available
            db_bind(config.get("database", "connection_string",
                "sqlite:////var/lib/nwu/nwu.db"))

    def __set_task(self, computer, task_type, *details):
        output = ''
        if len(details) == 0:
            show_help()
        computer = Computer.get_by(id=computer_id)
        details = " ".join(details)
        output += "Found %s in the database. Requesting %s of %s" % \
            (repr(computer), task_type, details)
        Tasks(computer=computer, action=task_type, details=details)
        session.flush()
        return output

    def cmd_forceinstall(self, computer, *packages):
        """Forces the installation of the specified package(s).
        """
        return self.__set_task(computer_id, 'forceinstall', *packages)

    def cmd_install(self, computer_id, *packages):
        """Installs the specified package(s).
        """
        return self.__set_task(computer_id, 'install', *packages)

    def cmd_addrep(self, computer_id, *details):
        """Adds a repository to the specified computer
        """
        
        return self.__set_task(computer_id, 'addrep', *details)

    def cmd_help(self):
        """Shows usage help.
        """
        show_help()

    def cmd_view(self, computer_id, detail=None):
        """View an specific info from the specified computer
        """
        if not detail:
            show_help()

        computer = Computer.get_by(id=computer_id)
        
        if not computer:
            print >> sys.stderr, "Specified computer not found in the database."
            sys.exit(1)
 
        details_map = {
            'packages' : 'current_packages',
            'update-candidates' : 'update_candidates',
            'repositories' : 'repositories',
            'tasks' : 'tasks'
            }

        try:
            read_table = getattr(computer, details_map[detail])
        except:
            show_help()

        output = "Reading %s from computer %s" % (detail, repr(computer))
        for i in read_table:
            # FIXME: define __repr__ in each db table class
            # and use some formatting feature like:
            #    fill = 45 - len(package.name)
            #    fill_blank = " " * fill
            #    print package.name + fill_blank +  package.version

            output += repr(i)
        return output

    def cmd_list(self, group=None):
        """List computers in the database.
    
        If the group name is provided, list only computers on
        that group.
        """
        output = ''
        if group == 'outdated':
            olds = {}
            # TODO: performance. use a single select, possibly with 'group by'
            for candidate in UpdateCandidates.query.all():
                olds[candidate.computer.id] = True
            for computer in Computer.query.all():
                if olds.has_key(computer.id):
                    output += "%s\t%s\t%s\n" % ( computer.id, \
computer.hostname, computer.os_name) 
        else:
            for computer in Computer.query.all():
                output += "%s\t%s\t%s\n" % ( computer.id, computer.hostname, \
computer.os_name)
        return output

