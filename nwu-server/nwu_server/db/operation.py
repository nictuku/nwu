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
from sqlalchemy import create_engine

log = logging.getLogger('nwu_server.db.operation')
# run this from somewhere else, or tests will brake
# from setup import read_conf

#cfg = read_conf()

#metadata.bind(cfg.connection_string)

def get_tbl_version(rpc_session,tbl):
    (uniq, token) = rpc_session

    if not Computer.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    query = session.query(TablesVersion).filter_by(tablename=tbl, 
        uniq=uniq)
    a = list(query)
    if len(a) > 0:
        return a[0].version
    else:
        return 0
     

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
# SA
class TablesVersion(Entity):
    using_options(tablename='tables_version')
    
    tablename = Field(String(255))
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

    def add_computer(password, iuniq, hostname, os_name, os_version):
        """Adds the given computer to the computers database.
        """
        log.info("Creating computer " + iuniq + " " + hostname + " " +\
             os_name + " " + os_version)
        m = session.save('Computer',uniq=iuniq,hostname=hostname, os_name=os_name,
            os_version=os_version,password=password)
        
        return True 

    def rpc_session_setup(uniq, token):
        """Sets up the rpc_session for agent-aggregator or agent-manager communication.

        The token string comes from the authentication process.

        Returns rpc_session object to be used by the agent in later
        communication steps.
        """
        log.info("Setting rpc_session for computer " + uniq + ".")
        # FIXME: test if token is valid here.
        check_m = Computer.get_by(uniq=uniq)
        password = ''

        if len(check_m) == 0:
            log.error("Problem in rpc_session auth for: %s" % uniq)
            return False

        if Computer.check_token(uniq, token):
            log.info("Computer authenticated: %s" % repr(check_m))
            return [ uniq, token ]

        # FIXME: return False or raise an exception?
        log.warn("Wrong token for: %s" % uniq)
        return False

    def check_token(uniq, token):
        """Checks if the specified token was generated using the stored
        computer password.
        """
        check_t = Computer.get_by(uniq=uniq)

        password = ''

        if not check_t:
            # No computer with that specified uniq id was found.
            return False
        else:
            for t in check_t:
                password = t.password

        valid_token = hmac.new(password, uniq).hexdigest()

        if valid_token == token:
            # Yeah, this is a valid token!
            return True
        else:
           return False

    rpc_session_setup=staticmethod(rpc_session_setup)
    check_token=staticmethod(check_token)
    add_computer=staticmethod(add_computer)

class CurrentPackages(Entity):
    using_options(tablename='current_packages')
    
    name = Field(String(255))
    version = Field(String(30))

    belongs_to('computer', of_kind='Computer', inverse='current_packages')
#    class sqlmeta:
#        defaultOrder = 'name'

    def set_list_diff(rpc_session, change_table, add_pkgs, rm_pkgs):
        """Takes two lists of packages, one for removal and one for
        addition, and update the specified table.
        """
        # Affects either CurrentPackages or UpdateCandidates

        (uniq, token) = rpc_session

        if not Computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        # old_names are used at the client-side and as db table names
        # NewNames are used for model operations
        mapper = { 'update_candidates' : 'UpdateCandidates',
            'current_packages' : 'CurrentPackages' } 
        # compatibility hack
        # FIXME: future versions of the database know what to do with apt or else
        change_table_name = change_table
        if change_table in mapper:
            change_table = mapper[change_table]

        if change_table not in ['UpdateCandidates', 'CurrentPackages']:
            raise Exception, 'Unknown table'
        table = eval(change_table)
        pkgs = {}
        if type(rm_pkgs) is dict:
            pkgs['rm_pkgs'] = rm_pkgs
        else:
            pkgs['rm_pkgs'] = {}

        if type(add_pkgs) is dict:
            pkgs['add_pkgs'] = add_pkgs
        else:
            pkgs['add_pkgs'] = {}

        client_computer = Computer.get_by(uniq=uniq)

        log.info("Updating %s for %s" % (change_table, repr(client_computer)))

        log.debug("going to delete: %s" % str(rm_pkgs))
        log.debug("going to update: %s" % str(add_pkgs))

        # Deleting old packages
        for del_pk_name, del_pk_version in pkgs['rm_pkgs'].iteritems():
            # FIXME: update history table here

            delitems= session.query(table).filter_by(name=del_pk_name,
                computer=client_computer)
            log.debug("Deleting %s entries" % len(delitems))
            session.delete(delitems)

        # Updating new packages
        # Deleting possible old entries for those packages
        for add_pk_name, add_pk_version in pkgs['add_pkgs'].iteritems():
            # FIXME: update history table here
            delitems = session.query(table).filter_by(name=add_pk_name,
                computer=client_computer)
            log.debug("Updating %s entries" % len(delitems))
            session.delete(delitems)
            new = table(computer=client_computer,name=add_pk_name,
                version=add_pk_version)

        # using db table name, not mapper name
        up = update_tbl_version(change_table_name, uniq)
        log.debug(repr(up))
        return up

    def set_current_packages_full(rpc_session, pkgs):
        (uniq, token) = rpc_session

        if not Computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"
        client_computer = Computer.get_by(uniq=uniq)

        log.debug("Updating current packages list for: %s" % repr(client_computer) )

        # Deleting old packages
        log.debug("Wiping old packages list.")

        delitems = session.query(CurrentPackages).filter_by(
            computer=client_computer)
        session.delete(delitems)

        log.debug("Adding new packages.")
        for pk_name, pk_version in pkgs.iteritems():
            CurrentPackages(computer=client_computer, name=pk_name,
                version=pk_version)
        up = update_tbl_version('current_packages', uniq)
        log.debug(repr(up))
 
        return up

    set_list_diff=staticmethod(set_list_diff)

class UpdateCandidates(Entity):
    using_options(tablename='update_candidates')

    name = Field(String(255))
    version = Field(String(30))

    belongs_to('computer', of_kind='Computer', inverse='update_candidates')

#    class sqlmeta:
#        defaultOrder = 'name'

    def set_update_candidates_full(rpc_session, pkgs):
        (uniq, token) = rpc_session

        if type(pkgs) is str:
            pkgs = {}

        if not Computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        client_computer = Computer.get_by(uniq=uniq)

        log.debug("Creating new update candidates list for: %s" %
             repr(client_computer)) 
        # Deleting old packages
        delitems = UpdateCandidates.query.filter_by(
            computer=client_computer)
        session.delete(delitems)

        for pk_name, pk_version in pkgs.iteritems():
            UpdateCandidates(Computer=client_computer, name=pk_name,
                version=pk_version)

        up = update_tbl_version('update_candidates', uniq)
        log.debug(repr(up))
        return up

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

    def set_repositories(rpc_session,reps):
        """Stores the full repositories list in the database, after
        wiping that computer's repositories table.
        """
        (uniq, token) = rpc_session
        if not Computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        client_computer = Computer.get_by(uniq=uniq)

        log.info("Updating repositories for %s" % repr(client_computer))
        # Deleting old reps
        delitems = Repositories.query.filter_by(computer=client_computer)

        session.delete(delitems)
        for source in reps:
            filename = source.pop(0)
            for repository in source:
                rep_elements = repository.split()

                rep_type = rep_elements[0]
                rep_uri = rep_elements[1]
                rep_distribution = rep_elements[2]
                rep_components = " ".join(rep_elements[3:])

                # update repositories
                setrep = Repositories(computer=client_computer, filename=filename,
                    type=rep_type, uri=rep_uri, distribution=rep_distribution,
                    components=rep_components)

        up = update_tbl_version('repositories', uniq)
        log.debug(repr(up))
        return up 

    # XXX: is this needed? 
    set_repositories=staticmethod(set_repositories)

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

def create_tables():
    """Creates required tables in the database.
    """
    log.debug("Creating necessary tables in the database.")
    setup_all()
    create_all()
#    os.unlink('/var/lib/nwu/nwu.db')
#    for table in ['Computer', 'CurrentPackages', 'UpdateCandidates',
#        'Repositories', 'Tasks', 'Users', 'TablesVersion']:
#        try:
#            t = eval(table)
#            t.createTable()
#        except:
#            print sys.exc_type, sys.exc_value
#            log.warning("Could not create table " + table + ": " + \
#                str(sys.exc_type) + '- ' + str(sys.exc_value))

if __name__ == '__main__':

    sys.exit(0)
    # FIXME: make a unit test so we can test db sanity
    create_tables()

    # FIXME: os name and version from sysinfo
    m = Computer(hostname='localhost', uniq='32109832109832109831209832190321weee', os_name='Linux', os_version='2.6.x')

    installed = CurrentPackages(computer=m, name='gcc', version='1.1')
    installed = CurrentPackages(computer=m, name='znes', version='4.1')
    reps = Repositories(computer=m, filename='/etc/apt/sources.list',type='deb',
        uri='http://blabla', distribution='stable',
        components = 'breezy-updates main restricted')
    ma = Computer.get_by(hostname='localhost')
    for package in ma.CurrentPackages:
        print package.name, package.version

    for rep in ma.repositorieses:
        print "REP:",rep.filename + ':' + rep.type, rep.uri, str(rep.components)
    #    help(ma)
        #print ma.aptCurrentPackageses.name, ma.aptCurrentPackageses.version
