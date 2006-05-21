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

"""Defines the nwu database scheme and tables.
"""
 
from sqlobject import *
from sqlobject.sqlbuilder import *
import sys
import hmac
import logging
from setup import PackageHub

log = logging.getLogger('nwu_server.db.operation')
#db_conf = setup.read_conf().connection_string
#conn = setup.cfg(db_conf).conn
#__connection__ = conn

hub = PackageHub()
__connection__ = hub

class computer(SQLObject):

    uniq = StringCol(length=32,alternateID=True)
    hostname = StringCol(length=255)
    password = StringCol(length=255)
    os_name = StringCol(length=255)
    os_version = StringCol(length=255)

    current_packages = MultipleJoin('apt_current_packages')
    update_candidates = MultipleJoin('apt_update_candidates')
    repositories = MultipleJoin('apt_repositories')
    authcomputer = MultipleJoin('authcomputer')
    task = MultipleJoin('task')

    def session_setup(self,uniq, token):
        """Sets up the session for agent-aggregator or agent-manager communication.

        The token string comes from the authentication process.

        Returns session object to be used by the agent in later
        communcation steps.
        """
    #    hub.begin()
    #    conn = hub.getConnection()
        log.info("Setting session for computer " + uniq + ".")

        # FIXME: test if token is valid here.
        query_check_m = computer.select(computer.q.uniq==uniq)
        check_m = list(query_check_m)
        log.debug("check")

        password = ''

    #    hub.commit()
    #    hub.end()
        if len(check_m) == 0:
            return False

        if self.check_token(uniq, token):
            return uniq, token

        # FIXME: return False or raise an exception?
        raise Exception, "Wrong token for " + uniq

    def check_token(uniq, token):
        """Checks if the specified token was generated using the stored
        computer password.
        """
#        hub.begin()
        query_check_t = computer.select(computer.q.uniq==uniq)
        check_t = list(query_check_t)

        password = ''

        if len(check_t) == 0:
            # No computer with that specified uniq id was found.
            return False
        else:
            for t in check_t:
                password = t.password

        valid_token = hmac.new(password, uniq).hexdigest()

#        hub.commit()
#        hub.end()
        if valid_token == token:
            # Yeah, this is a valid token!
            return True
        else:
            return False

    session_setup=classmethod(session_setup)
    check_token=staticmethod(check_token)    

class authcomputer(SQLObject):

    password = StringCol(length=255)

    computer = ForeignKey('computer')

class apt_current_packages(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    computer = ForeignKey('computer')
    class sqlmeta:
        defaultOrder = 'name'

class apt_update_candidates(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    computer = ForeignKey('computer')
    class sqlmeta:
        defaultOrder = 'name'


class apt_repositories(SQLObject):
    """APT repositories table.
    Example:

    deb http://de.archive.ubuntu.com/ubuntu breezy-updates main restricted

    Respective field names:
    deb uri distribution [component1] [component2] [...]
    """

    filename = StringCol() # eg: '/etc/apt/sources.list'
    type = StringCol(length=30) # eg: deb, deb-src
    uri = StringCol()
    distribution = StringCol(length=255)
    components = StringCol() # space separated list of components

    computer = ForeignKey('computer')

class task(SQLObject):
    
    action = StringCol(length=255)
    details = StringCol(default=None)
    computer = ForeignKey('computer')

class users(SQLObject):

    username = StringCol(length=255, unique=True)
    password = StringCol(length=255)
    userlevel=IntCol()
            

if __name__ == '__main__':

    create_tables()

    # FIXME: os name and version from sysinfo
    m = computer(hostname='localhost', uniq='32109832109832109831209832190321weee', os_name='Linux', os_version='2.6.x')

    installed = apt_current_packages(computer=m, name='gcc', version='1.1')
    installed = apt_current_packages(computer=m, name='znes', version='4.1')
    
    reps = apt_repositories(computer=m, filename='/etc/apt/sources.list',type='deb',
        uri='http://blabla', distribution='stable',
        components = 'breezy-updates main restricted')

    all = computer.select(computer.q.hostname=='localhost')

    #print "weee",list(all)

    for ma in all:
        print ma.hostname
        for package in ma.apt_current_packageses:
            print package.name, package.version

        for rep in ma.apt_repositorieses:
            print "REP:",rep.filename + ':' + rep.type, rep.uri, str(rep.components)
    #    help(ma)
        #print ma.aptCurrentPackageses.name, ma.aptCurrentPackageses.version
