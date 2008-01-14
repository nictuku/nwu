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
# FIXME: wildcard imports should not be used
from elixir import *

log = logging.getLogger('nwu.server.db.model')

new_map = { 'update_candidates' : 'UpdateCandidates',
    'current_packages' : 'CurrentPackages',
    'repositories' : 'Repositories',
    'tasks' : 'Tasks',
    'account': 'Account'}

class TablesVersion(Entity):
    using_options(tablename='tables_version')
    
    name = Field(String(255))
    version = Field(Integer)
    uniq = Field(String(32))

class Computer(Entity):
    using_options(tablename='computer')

    uniq = Field(String(32),unique=True)
    hostname = Field(String(255))
    os_name = Field(String(255))
    os_version = Field(String(255))
    
    has_many('current_packages', of_kind='CurrentPackages',inverse='computer')
    has_many('update_candidates', of_kind='UpdateCandidates',inverse='computer')
    has_many('repositories', of_kind='Repositories',inverse='computer')
    has_many('tasks', of_kind='Tasks')

    belongs_to('account', of_kind='Account', required=False)

    def __repr__(self):
        return '<Computer %s(%s)>' % (self.hostname, self.id)

    def to_dict(self):
        account_id = 0
        if self.account:
            account_id = self.account.oid
        return {'id': self.oid, 'hostname': self.hostname, 
                'os_name': self.os_name, 'os_version': self.os_version,
                'account_id': account_id}

class CurrentPackages(Entity):
    using_options(tablename='current_packages')
    
    name = Field(String(255))
    version = Field(String(30))
    
    def to_dict(self):
        return {'id': self.oid, 'name': self.name, 'version': self.version}

    belongs_to('computer', of_kind='Computer', inverse='current_packages')
#    class sqlmeta:
#        defaultOrder = 'name'

class UpdateCandidates(Entity):
    using_options(tablename='update_candidates')

    name = Field(String(255))
    version = Field(String(30))

    def to_dict(self):
        return {'id': self.oid, 'name': self.name, 'version': self.version}

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

    def to_dict(self):
        return {'id': self.oid, 'filename': self.filename, 'type': self.type,
                'uri': self.uri, 'distribution': self.distribution,
                'components': self.components}

    belongs_to('computer', of_kind='Computer', inverse='repositores')

class Tasks(Entity):
    using_options(tablename='tasks')

    action = Field(String(255))
    details = Field(String)

    def to_dict(self):
        return {'id': self.oid, 'action': self.action, 
                'details': self.details }

    belongs_to('computer', of_kind='Computer', inverse='tasks')

class Account(Entity):
    using_options(tablename='account')
    
    name = Field(String(255), unique=True)
    csr = Field(String, unique=True)
    cert_serial_number = Field(Integer, default=-1)
    cert = Field(String, default=None)
    privileges = Field(Integer, default=0)

    has_one('computer', of_kind='Computer', inverse='account')

    def to_dict(self):
        computer_id = 0
        if self.computer:
            computer_id = self.computer.oid

        return {'id': self.oid, 'name': self.name, 'csr': self.csr,
                'cert_serial_number': self.cert_serial_number,
                'cert': self.cert, 'privileges': self.privileges,
                'computer_id': computer_id}

    def __repr__(self):
        return '<Account: %s>' % (self.name)
        

def db_bind(connection_string, rebind=False):
    """ Binds a database connection. """
    if not metadata.is_bound() or rebind:
        metadata.bind = connection_string
        setup_all()
        return True
    return False

def create_tables():
    """Creates required tables in the database.
    """
    if not metadata.is_bound():
        raise Exception('Database connection not initialized yet.')
    log.debug("Creating necessary tables in the database.")
    create_all()
    session.flush()
