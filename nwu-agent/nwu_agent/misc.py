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

from SOAPpy import *
import os
import logging
#from xml.sax.saxutils import escape as xmlescape
import sysinfo
import string
import random
import hmac
import stat
import ConfigParser

config = ConfigParser.ConfigParser()
r = config.read("/etc/nwu/agent.conf")

server_uri = config.get("connection", "server_uri")

# grr I don't want to have to do this. Fix sysinfo
format = "%(asctime)s cacic[%(process)d] %(levelname)s %(name)s:%(lineno)d: %(message)s"
sysinfo_logger = logging.getLogger("sysinfo")
sysinfo_logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(format)
ch.setFormatter(formatter)
sysinfo_logger.addHandler(ch)

Config.simplify_objects = 1 
rpc = SOAPProxy(server_uri)

def get_auth():
    auth_path = "/var/spool/nwu/auth"

    try:
        st = os.stat(auth_path)
    except:
        pass
    else:
        mode = st[stat.ST_MODE]
        if mode != 33216 and mode != 33152: # 600 and 700
            raise Exception, "Wrong permission for the auth file (" +\
              auth_path + "). See the README file."

    r = os.umask(0177)

    auth_file = ConfigParser.ConfigParser()
    # FIXME: create new file if needed
    r = auth_file.read(auth_path)

    changed = False

    if not auth_file.has_section('auth'):
        auth_file.add_section('auth')

        changed = True

    if not auth_file.has_option('auth', 'uniq') or \
        len(auth_file.get("auth", "uniq")) != 32:
        # No or bad uniq string found in the auth file. Creating a new one.

        letters = string.ascii_uppercase + string.digits
        uniq = ''
        for i in range(32):
            uniq += random.choice(letters)

        auth_file.set("auth", "uniq", uniq)
        changed = True
#
    else:
        uniq = auth_file.get("auth", "uniq")
        print "uniq:", uniq

    # Checking for password. If it doesn't find one, generate
    # a new random string.

    # FIXME: Security issue: is variable length password creation a good idea? 
    # FIXME: Security issue: should the server create a password instead?

    if not auth_file.has_option('auth', 'password') or \
        len(auth_file.get("auth", "password")) != 255:
 
       # Creating a new password string of 255 bytes.
        password = ''
        letters = string.ascii_letters + string.digits
        for i in range(255):
            password += random.choice(letters)
        
        auth_file.set("auth", "password", password)
        changed = True

    else:
        password = auth_file.get("auth", "password")
        print "password:", password


    # dump changes
    if changed:
        print "Storing auth settings to", auth_path
        auth_fd = open(auth_path, 'w')
        auth_file.write(auth_fd)
        auth_fd.close()

    session = uniq, password

    return session

 
# FIXME: make this a class and use instance
def get_packages():
#    import pdb ; pdb.set_trace()
    pkgs = sysinfo.software.packages()
    print pkgs
    return pkgs

pkgs = get_packages()

def get_current_packages():
    #get_packages()
    packages = pkgs.installed_ver
    return packages


def get_apt_update_candidates():
    #get_packages()
    update_candidates = pkgs.update_candidates
    return update_candidates    
    
def list_sources_list():
    filenames = ['/etc/apt/sources.list']
    directories = ['/etc/apt/sources.d']

    for dir in directories:

        try:
            for file in os.listdir(dir):
                if file.endswith('.list'):
                    filenames.append(dir + '/' + file)
        except:
            pass
    return filenames

# FIXME: move this to sysinfo
def read_sources_list(filenames):
    repositories = []

    for source in filenames:
        # any use to handle exceptions here?
        f = open(source, 'r')
        thisrep = [source]

        for line in f:
             line = line.strip()
             #ignore comments and blank lines
             l = line.split('#',1)[0]
             ignore = re.search(r'^$|#|^\s+$', l)

             if not ignore :
                thisrep.append(l)
    #pik = pickle.dumps(repositories)

        repositories.append(thisrep)

    print repositories
    return repositories

def store_spool(task_list):
    """Stores data in the services pool directory.
    
    It takes a list of tasks, each of which contains a touple of
    actions and details for execution.

    Security is a must here."""
    # FIXME: check for right permissions in the spool dir and files

    task_spool_path = "/var/spool/nwu/nw.tasks"

    store = ConfigParser.ConfigParser()

    r = store.read(task_spool_path)

    for tk in task_list:

        type = tk[0]
        action = tk[1]

        print repr(action)

        if action == None:
            action = '-'

        print "received task, type="+ str(type) + " , action="+ str(action)
        
        if not store.has_section(type):
            # create section in the task file
            store.add_section(type)

        if not store.has_option(type, action):
            # add action to the task file
            # None is the action detail, reserved for future need
            store.set(type, action, None)

    try:
        updt_spool = open(task_spool_path, 'w')
    except:
        print "!!! Problem writing to spool directory in", task_spool_path
        pass
    else:
        print "Updating task spool file."
        store.write(updt_spool)

