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

"""Defines the nwu database scheme, tables and operations.
"""
import sys
import hmac
import logging
from elixir import *
import ConfigParser

log = logging.getLogger('nwu_server.db.model')

new_map = { 'update_candidates' : 'UpdateCandidates',
    'current_packages' : 'CurrentPackages',
    'repositories' : 'Repositories',
    'tasks' : 'Tasks' }

class TablesVersion(Entity):
    using_options(tablename='tables_version')
    
    name = Field(String(255))
    version = Field(Integer)
    uniq = Field(String(32))

class Computer(Entity):
    using_options(tablename='computer')

    uniq = Field(String(32),unique=True)
    hostname = Field(String(255))
    password = Field(String(255))
    os_name = Field(String(255))
    os_version = Field(String(255))
    
    has_many('current_packages', of_kind='CurrentPackages',inverse='computer')
    has_many('update_candidates', of_kind='UpdateCandidates',inverse='computer')
    has_many('repositories', of_kind='Repositories',inverse='computer')
    has_many('tasks', of_kind='Tasks')

    def __repr__(self):
        return '<Computer %s(%s)>' % (self.hostname, self.id)

class CurrentPackages(Entity):
    using_options(tablename='current_packages')
    
    name = Field(String(255))
    version = Field(String(30))

    belongs_to('computer', of_kind='Computer', inverse='current_packages')
#    class sqlmeta:
#        defaultOrder = 'name'

class UpdateCandidates(Entity):
    using_options(tablename='update_candidates')

    name = Field(String(255))
    version = Field(String(30))

    belongs_to('computer', of_kind='Computer', inverse='update_candidates')

#    class sqlmeta:
#        defaultOrder = 'name'

class Repositories(Entity):
    """APT repositories table.
    Example:

    deb http://de.archive.ubuntu.com/ubuntu breezy-updates main restricted

    Respective field names:
    deb uri distribution [component1] [component2] [...]
    """
    using_options(tablename='repositories')

    filename = Field(String) # eg: '/etc/apt/sources.list'
    type = Field(String(30)) # eg: deb, deb-src
    uri = Field(String)
    distribution = Field(String(255))
    components = Field(String) # space separated list of components

    belongs_to('computer', of_kind='Computer', inverse='repositores')

class Tasks(Entity):
    using_options(tablename='tasks')

    action = Field(String(255))
    details = Field(String)

    belongs_to('computer', of_kind='Computer', inverse='tasks')

class Users(Entity):
    using_options(tablename='users')

    username = Field(String(255), unique=True)
    password = Field(String(255))
    userlevel= Field(Integer)

def create_tables(config):
    """Creates required tables in the database.
    """
    log.debug("Creating necessary tables in the database.")
    metadata.bind=config['connection_string']
    setup_all()
    create_all()

def read_config():
    """Reads configuration data from the config file.
    """
    config_p = ConfigParser.ConfigParser()
    config_p.read("/etc/nwu/server.conf")

    host = config_p.get("webservice", "host").lower()
    port = int(config_p.get("webservice", "port"))
    db_type = config_p.get("database", "type")
    db_host = config_p.get("database", "host")
    db_database = config_p.get("database", "database")
    db_user = config_p.get("database", "user")
    db_password = config_p.get("database", "password")
    log.info("db: Using " + db_type + " as database backend.")
    connection_string = db_type + "://" + db_user + ":" + \
       db_password + "@" + db_host + "/" + db_database

    config = { 'host' : host,
    'port' : port,
    'pemfile' : '/etc/nwu/server.pem',
    'databasetype' : db_type,
    'connection_string' : connection_string,
    }
    return config

if __name__ == '__main__':

    sys.exit(0)
