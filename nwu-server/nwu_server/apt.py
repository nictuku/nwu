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

# FIXME: there is a lot of code repetition here, you insane coder

def apt_set_repositories(session,reps):
    """Stores the full repositories list in the database, after
    wiping that machine's repositories table.
    """

    (uniq, token) = session

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    mach = machine.select(machine.q.uniq==uniq)
    l = list(mach)
    q = len(l)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " machine(s) with'" + uniq + "\
'uniq string and it should have exactly one."

    client_machine = l[0]

    print "Updating repositories for:", client_machine.id, client_machine.hostname
    print dir(client_machine)
    # Deleting old reps

    delquery = conn.sqlrepr(Delete(apt_repositories.q, where=\
        (apt_repositories.q.machineID ==  client_machine.id)))

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
                print "repeated distro:", k

            # update repositories
            setrep = apt_repositories(machine=client_machine, filename=filename,
                type=rep_type, uri=rep_uri, distribution=rep_distribution,
                components=rep_components)


#        setrep = apt_repositories(machine=mach, filename=filename,rep_type='deb',
#        rep_uri='http://de.archive.ubuntu.com/ubuntu',
#        components = 'breezy-updates main restricted')
    return True



def apt_set_upgrade_candidates_diff(session, add_pkgs, rm_pkgs):
#    import pdb ; pdb.set_trace()
    (uniq, token) = session

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



    mach = machine.select(machine.q.uniq==uniq)
    l = list(mach)
    q = len(l)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " machine(s) with'" + uniq + "\
'uniq string and it should have exactly one."

    client_machine = l[0]

    print "Updating upgrade candidates list for:", client_machine.id, client_machine.hostname

    # Deleting old packages
    for del_pk_name, del_pk_version in pkgs['rm_pkgs'].iteritems():
        # FIXME: update history table here


        print "Deleting old entries:", del_pk_name, del_pk_version
        delquery = conn.sqlrepr(Delete(apt_upgrade_candidates.q, where=\
            (apt_upgrade_candidates.q.name==del_pk_name)))

        conn.query(delquery)

    # Updating new packages
    # Deleting possible old entries for those packages

    for add_pk_name, add_pk_version in pkgs['add_pkgs'].iteritems():
        # FIXME: update history table here
        print "Updating new entries for:", add_pk_name, add_pk_version
        delquery = conn.sqlrepr(Delete(apt_upgrade_candidates.q, where=\
            (apt_upgrade_candidates.q.name==add_pk_name)))

        conn.query(delquery)

        apt_upgrade_candidates(machine=client_machine, name=add_pk_name,
            version=add_pk_version)

    return True



def apt_set_upgrade_candidates_full(session, pkgs):
#    import pdb ; pdb.set_trace()
    (uniq, token) = session

    if type(pkgs) is str:  
        pkgs = {} 

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    mach = machine.select(machine.q.uniq==uniq)
    l = list(mach)
    q = len(l)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " machine(s) with'" + uniq + "\
'uniq string and it should have exactly one."

    client_machine = l[0]

    print "Creating new upgrade candidates list for:", client_machine.id, client_machine.hostname

    # Deleting old packages

    delquery = conn.sqlrepr(Delete(apt_upgrade_candidates.q, where=\
        (apt_upgrade_candidates.q.machineID ==  client_machine.id)))

    conn.query(delquery)

    for pk_name, pk_version in pkgs.iteritems():
    #    print pk_name, pk_version
        apt_upgrade_candidates(machine=client_machine, name=pk_name,
            version=pk_version)

    return True

def apt_set_current_packages_full(session, pkgs):
    (uniq, token) = session

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    mach = machine.select(machine.q.uniq==uniq)
    l = list(mach)
    q = len(l)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " machine(s) with'" + uniq + "\
'uniq string and it should have exactly one."

    client_machine = l[0]

    print "Updating current packages list for:", client_machine.id, client_machine.hostname

    # Deleting old packages
    print "Wiping old packages list."
    delquery = conn.sqlrepr(Delete(apt_current_packages.q, where=\
        (apt_current_packages.q.machineID ==  client_machine.id)))

    conn.query(delquery)
    print "Adding new packages."
    for pk_name, pk_version in pkgs.iteritems():
    #    print pk_name, pk_version
        apt_current_packages(machine=client_machine, name=pk_name,
            version=pk_version)
    print "End."
    return True
