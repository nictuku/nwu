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
import ConfigParser
import logging

log = logging.getLogger('nwu_server.db.operation')

#FIXME: Organize this properly, object-oriented

config = ConfigParser.ConfigParser()
config.read("/etc/nwu/server.conf")

db_type = config.get("database", "type")
db_host = config.get("database", "host")
db_database = config.get("database", "database")
db_user = config.get("database", "user")
db_password = config.get("database", "password")


log.debug("Using" + db_type + " as my database.")

if db_type == 'sqlite':
    connection_string = db_type + "://" + db_database
else:
    connection_string = db_type + "://" + db_user + ":" + db_password + "@" +\
     db_host + "/" + db_database

log.debug("conn string:" + connection_string)

conn = connectionForURI(connection_string)

conn.debug=0

__connection__ = conn



class machine(SQLObject):

    uniq = StringCol(length=32,alternateID=True)
    hostname = StringCol(length=255)
    password = StringCol(length=255)
    os_name = StringCol(length=255)
    os_version = StringCol(length=255)

    current_packages = MultipleJoin('apt_current_packages')
    update_candidates = MultipleJoin('apt_update_candidates')
    repositories = MultipleJoin('apt_repositories')
    auth = MultipleJoin('auth')
    task = MultipleJoin('task')

class auth(SQLObject):

    password = StringCol(length=255)

    machine = ForeignKey('machine')

class apt_current_packages(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    _defaultOrder = 'name'

    machine = ForeignKey('machine')

class apt_update_candidates(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    _defaultOrder = 'name'

    machine = ForeignKey('machine')


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

    machine = ForeignKey('machine')

class task(SQLObject):
    
    action = StringCol(length=255)
    details = StringCol(default=None)
    machine = ForeignKey('machine')

class users(SQLObject):

    username = StringCol(length=255)
    password = StringCol(length=255)
    userlevel=IntCol()
            
def create_tables():
    """Creates required tables in the database.
    """
    log.debug("Creating necessary tables in the database.")
    try:
        machine.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
             str(sys.exc_value))
    try:
        apt_current_packages.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
            str(sys.exc_value))
    try:
        apt_update_candidates.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
             str(sys.exc_value))
    try:
        apt_repositories.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
            str(sys.exc_value))
    try:
        task.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
            str(sys.exc_value))
    try:
        auth.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
            str(sys.exc_value))
    try:
        users.createTable()
    except:
        log.warning("Could not create table " + str(sys.exc_type) + ' ' +\
             str(sys.exc_value))
 

if __name__ == '__main__':

    create_tables()

    # FIXME: os name and version from sysinfo
    m = machine(hostname='localhost', uniq='32109832109832109831209832190321weee', os_name='Linux', os_version='2.6.x')

    installed = apt_current_packages(machine=m, name='gcc', version='1.1')
    installed = apt_current_packages(machine=m, name='znes', version='4.1')
    
    reps = apt_repositories(machine=m, filename='/etc/apt/sources.list',type='deb',
        uri='http://blabla', distribution='stable',
        components = 'breezy-updates main restricted')

    all = machine.select(machine.q.hostname=='localhost')

    #print "weee",list(all)

    for ma in all:
        print ma.hostname
        for package in ma.apt_current_packageses:
            print package.name, package.version

        for rep in ma.apt_repositorieses:
            print "REP:",rep.filename + ':' + rep.type, rep.uri, str(rep.components)
    #    help(ma)
        #print ma.aptCurrentPackageses.name, ma.aptCurrentPackageses.version
