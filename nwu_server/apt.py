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


from db.operation import *
import auth
import logging

log = logging.getLogger('nwu_server.apt')

# FIXME: there is a lot of code repetition here, you insane coder
hub = PackageHub()
__connection__ = hub
def apt_set_repositories(session,reps):
    """Stores the full repositories list in the database, after
    wiping that computer's repositories table.
    """
    (uniq, token) = session
    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"
   
    conn = hub.getConnection()
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

    delquery = conn.sqlrepr(Delete(apt_repositories.q, where=\
        (apt_repositories.q.computerID ==  client_computer.id)))

    conn.query(delquery)

    #rep_data = pickle.loads(reps)

    
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


#        setrep = apt_repositories(computer=mach, filename=filename,
            # rep_type='deb',
#        rep_uri='http://de.archive.ubuntu.com/ubuntu',
#        components = 'breezy-updates main restricted')
    return True

def apt_set_list_diff(session, change_table, add_pkgs, rm_pkgs):
#    import pdb ; pdb.set_trace()
    (uniq, token) = session

    if change_table not in ['apt_update_candidates', 'apt_current_packages']:
        raise Exception, 'Unknown table'

    table = eval(change_table)

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"
   
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

    return True


def apt_set_update_candidates_full(session, pkgs):
#    import pdb ; pdb.set_trace()
    (uniq, token) = session

    if type(pkgs) is str:  
        pkgs = {} 

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"
    conn = hub.getConnection()

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

    return True

def apt_set_current_packages_full(session, pkgs):
    (uniq, token) = session

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"
    conn = hub.getConnection()

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
    return True
