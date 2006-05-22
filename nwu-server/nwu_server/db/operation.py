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
 
from sqlobject import *
from sqlobject.sqlbuilder import *
import sys
import hmac
import logging
from setup import PackageHub

log = logging.getLogger('nwu_server.db.operation')

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
    
    def add_computer(password, uniq, hostname, os_name, os_version):
        """Adds the given computer to the computers database.
        """
    #    import pdb; pdb.set_trace()
        conn = hub.getConnection()
        hub.begin()
        log.info("Creating computer " + uniq + " " + hostname + " " +\
             os_name + " " + os_version)
        m = computer(uniq=uniq,hostname=hostname, os_name=os_name,
            os_version=os_version,password=password)

        hub.commit()
        hub.end()
        return True

    def session_setup(self,uniq, token):
        """Sets up the session for agent-aggregator or agent-manager communication.

        The token string comes from the authentication process.

        Returns session object to be used by the agent in later
        communcation steps.
        """
        log.info("Setting session for computer " + uniq + ".")

        # FIXME: test if token is valid here.
        query_check_m = computer.select(computer.q.uniq==uniq)
        check_m = list(query_check_m)
        log.debug("check")

        password = ''

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

        if valid_token == token:
            # Yeah, this is a valid token!
            return True
        else:
            return False

    session_setup=classmethod(session_setup)
    check_token=staticmethod(check_token)
    add_computer=staticmethod(add_computer)

class authcomputer(SQLObject):

    password = StringCol(length=255)

    computer = ForeignKey('computer')

class apt_current_packages(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    computer = ForeignKey('computer')
    class sqlmeta:
        defaultOrder = 'name'

    def apt_set_list_diff(session, change_table, add_pkgs, rm_pkgs):
        """Takes two lists of packages, one for removal and one for
        addition, and update the specified table.
        """
        # Affects either apt_current_packages or apt_update_candidates

        (uniq, token) = session

        if not computer.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        if change_table not in ['apt_update_candidates', 'apt_current_packages']:
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

        conn = hub.getConnection()
        hub.begin()

        mach = computer.select(computer.q.uniq==uniq)
        l = list(mach)
        q = len(l)
        if q != 1:
            raise Exception, "Strange. There are " +  q +  " computer(s) with'" +\
                uniq + "'uniq string and it should have exactly one."

        client_computer = l[0]

        log.debug("Updating table " + change_table + " for " + \
           client_computer.hostname + '(' + str(client_computer.id) + ')' )

        log.debug("will delete: " + str(rm_pkgs))
        log.debug("will update: " + str(add_pkgs))

        # Deleting old packages
        for del_pk_name, del_pk_version in pkgs['rm_pkgs'].iteritems():
            # FIXME: update history table here


            log.debug("Deleting old entries " + del_pk_name + " " + del_pk_version)
            delquery = conn.sqlrepr(Delete(table.q, where=\
                (table.q.name==del_pk_name)))

            conn.query(delquery)

        # Updating new packages
        # Deleting possible old entries for those packages
        for add_pk_name, add_pk_version in pkgs['add_pkgs'].iteritems():
            # FIXME: update history table here
            log.debug("Updating new entries for " + add_pk_name + " " + \
                add_pk_version)
            delquery = conn.sqlrepr(Delete(table.q, where=\
                (table.q.name==add_pk_name)))

            conn.query(delquery)

            table(computer=client_computer, name=add_pk_name,
                version=add_pk_version)

        hub.commit()
        hub.end()
        return True

    def apt_set_current_packages_full(session, pkgs):
        (uniq, token) = session

        if not auth.check_token(uniq, token):
            raise Exception, "Invalid authentication token"
        conn = hub.getConnection()
        hub.begin()
        mach = computer.select(computer.q.uniq==uniq)
        l = list(mach)
        q = len(l)
        if q != 1:
            raise Exception, "Strange. There are " +  q +  " computer(s) with'" + \
                uniq + "'uniq string and it should have exactly one."

        client_computer = l[0]

        log.debug("Updating current packages list for: " \
            + client_computer.hostname + '(' + str(client_computer.id) + ')' )

        # Deleting old packages
        log.debug("Wiping old packages list.")

        delquery = conn.sqlrepr(Delete(apt_current_packages.q, where=\
            (apt_current_packages.q.computerID ==  client_computer.id)))

        conn.query(delquery)
        log.debug("Adding new packages.")

        for pk_name, pk_version in pkgs.iteritems():
            apt_current_packages(computer=client_computer, name=pk_name,
                version=pk_version)
        log.debug("End.")
        hub.commit()
        hub.end()
        return True


class apt_update_candidates(SQLObject):

    name = StringCol(length=255)
    version = StringCol(length=30)
    computer = ForeignKey('computer')
    class sqlmeta:
        defaultOrder = 'name'

    def apt_set_update_candidates_full(session, pkgs):
    #    import pdb ; pdb.set_trace()
        (uniq, token) = session

        if type(pkgs) is str:
            pkgs = {}

        if not auth.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        conn = hub.getConnection()
        hub.begin()
        mach = computer.select(computer.q.uniq==uniq)
        l = list(mach)
        q = len(l)
        if q != 1:
            raise Exception, "Strange. There are " +  q +  " computer(s) with'" +\
                uniq + "'uniq string and it should have exactly one."

        client_computer = l[0]

        log.debug("Creating new update candidates list for: " \
            + client_computer.hostname + '(' + str(client_computer.id) + ')')

        # Deleting old packages
        delquery = conn.sqlrepr(Delete(apt_update_candidates.q, where=\
            (apt_update_candidates.q.computerID ==  client_computer.id)))
        conn.query(delquery)

        for pk_name, pk_version in pkgs.iteritems():
            apt_update_candidates(computer=client_computer, name=pk_name,
                version=pk_version)
        hub.commit()
        hub.end()
        return True

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

    def apt_set_repositories(session,reps):
        """Stores the full repositories list in the database, after
        wiping that computer's repositories table.
        """
        (uniq, token) = session
        if not auth.check_token(uniq, token):
            raise Exception, "Invalid authentication token"

        conn = hub.getConnection()
        hub.begin()
        mach = computer.select(computer.q.uniq==uniq)
        l = list(mach)
        q = len(l)
        if q != 1:
            raise Exception, "Strange. There are " +  str(q) +  \
        " computer(s) with'" + uniq + \
        "'uniq string and it should have exactly one."

        client_computer = l[0]

        log.info("Updating repositories for: " + client_computer.hostname + \
            '(' + str(client_computer.id) + ')' )

        # Deleting old reps
        conn = hub.getConnection()
        delquery = conn.sqlrepr(Delete(apt_repositories.q, where=\
            (apt_repositories.q.computerID ==  client_computer.id)))

        conn.query(delquery)

        for source in reps:
            filename = source.pop(0)
            for repository in source:
                rep_elements = repository.split()

                rep_type = rep_elements[0]
                rep_uri = rep_elements[1]
                rep_distribution = rep_elements[2]
                rep_components = " ".join(rep_elements[3:])

                # If repeated distro, just update components
                distro_check = apt_repositories.select(AND(
                apt_repositories.q.type==rep_type,apt_repositories.q.uri==rep_uri,
                apt_repositories.q.distribution==rep_distribution))

                for k in distro_check:
                    log.debug("repeated distro: " +  str(k))

                # update repositories
                setrep = apt_repositories(computer=client_computer, filename=filename,
                    type=rep_type, uri=rep_uri, distribution=rep_distribution,
                    components=rep_components)

        hub.commit()
        hub.end()
        return True


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
