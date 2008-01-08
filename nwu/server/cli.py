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
from nwu.server.db.model import session, metadata, setup_all

# XXX: What about using nwu.common.config directly?
from nwu.server.config import read_config

VERSION = '0.1.7'

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
    "adduser" : "<name> <level:0|1>     : Add a new user, admin or not",
    "addrep" : " <computer> <repository uri>  : Add new repository",
        
    }

    def __init__(self, config=None, initialize=True):
        if initialize:
            if not config:
                config = read_config()
            metadata.bind = config['connection_string']
            setup_all()

    def cmd_help(self):
        self.usage()

    def cmd_forceinstall(self, computer, *packages):
        output = ''
        if len(packages) == 0:
            self.usage()
        computer = Computer.get_by(id=computer)
        packages = " ".join(packages)
        output += "Found %s in the database. Requesting forceinstall of %s" % \
            (repr(computer), packages)
        Tasks(computer=computer, action='forceinstall', details=packages)
        session.flush()
        return output

    def cmd_list(self, group=None):
        output = ''
        if group == 'outdated':
            olds = {}
            # TODO: performance. use a single select, possibly with 'group by'
            for candidate in UpdateCandidates.query.select():
                olds[candidate.computer.id] = True
            for computer in Computer.query.select():
                if olds.has_key(computer.id):
                    output += "%s\t%s\t%s\n" % ( computer.id, \
computer.hostname, computer.os_name) 
        else:
            for computer in Computer.query.select():
                output += "%s\t%s\t%s\n" % ( computer.id, computer.hostname, \
computer.os_name)
        return output

#    this is for the 'admin' features, which are currently disabled
#
#    def cmd_adduser(self, username, level):
#            if not self.is_safe(username):
#                print """Username should consist of letters, digits, \
# underscores periods and dashes.
#"""
#                sys.exit(64)
#            password = md5(p).hexdigest()
#            try:
#                u = users(username=username, userlevel=level,password=password)
#            except:
#                print "Error adding user. Username duplicated?"


    def usage(self):
        print \
    """Usage: nwu <command> <options> [arguments]
    Command line manager for NWU, version """ + VERSION + """.

    Available commands:
    """

        cmds = self.commands.keys()
        cmds.sort()
        for cmd in cmds:
            print "  " + cmd  + " " + self.commands[cmd] 

        print """
    Available groups for list command:

        outdated
    """
        sys.exit(64)

def is_safe(str, http=False):
    # FIXME: duplicated code. see nwu_agent/maint. candidate for nwu-common
    # From Byron Ellacot's message in the mod_python list
    # http://www.modpython.org/pipermail/mod_python/2004-December/016987.html

    ok_chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_"

    # We can also selectively accept other chars

    if http:
        ok_chars += "/: "

    return [x for x in str if x.lower() not in ok_chars] == []

def main():
    args = len(sys.argv)

    if args < 2 or sys.argv[1] not in commands:

        print \
    """Type 'nwu help' for usage help

    NWU is a remote upgrades manager for apt-able systems.
    For more information, see https://dev.ubuntubrasil.org/trac/nwu/
    """ 

        sys.exit(64) # see /usr/include/sysexits.h

    sub_command = sys.argv[1]

    args = []

    config = read_config()
    metadata.bind = config['connection_string']
    setup_all()


    if len(sys.argv) > 2:
        args = sys.argv[2:]

    elif sub_command == 'view':

        if len(args) > 1:
            id = args[0]
            mach = Computer.get_by(id=id)
            view_what = args[1]

            if view_what == 'packages':
                print "Reading current packages in computer %s" % repr(mach)
                for package in mach.current_packages:
                    fill = 45 - len(package.name)
                    fill_blank = " " * fill 
                    print package.name + fill_blank +  package.version

            elif view_what == 'update-candidates':
                print "Reading update candidades for computer %s" % repr(mach)
                for package in mach.update_candidates:
                    fill = 45 - len(package.name)
                    fill_blank = " " * fill 
                    print package.name  + fill_blank + package.version

            elif view_what == 'repositories':
                print "Reading repositories for computer %s" % repr(mach)
                for rep in mach.repositories:
                    print rep.type + " " + rep.uri + " " + rep.distribution + \
                        " " + rep.components + "  (" + rep.filename + ")"

            elif view_what == 'tasks':
                print "Reading tasks for computer %s" % repr(mach) 
                for task in mach.tasks:
                    print task.action + ": " + str(task.details)

            else: usage()

        elif len(args) == 1:
            print """Please choose an information to view:

    packages, repositories, update-candidates, tasks
    """

        else: usage() 

    elif sub_command == 'update' or sub_command == 'upgrade':

        if len(args) > 0:
            id = args[0]
            ma = Computer.get_by(id=id)
            print "Found computer id=" + id + " in the database. Requesting\
 " + sub_command + "."
            Tasks(computer=mach, action=sub_command)
        else:
            usage()
        
    elif sub_command == 'install' or sub_command == 'addrep' or \
sub_command == 'forceinstall':
        if len(args) > 1:
            id = args[0]
            details = " ".join(args[1:])
            m = Computer.get_by(id=id)
            ma = list(m)
            for mach in ma:
                print "Found computer id=" + id + " in the database. Requesting\
 " + sub_command + " " + details + "."
                Tasks(computer=mach, action=sub_command, details=details)
        else:
            usage()

if __name__ == '__main__':

    main()
