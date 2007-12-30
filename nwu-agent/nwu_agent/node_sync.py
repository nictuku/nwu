#!/usr/bin/python
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

import hmac
import logging
import os
from nwu_agent.talk import agent_talk
import ConfigParser

log = logging.getLogger("nwu_agent.node_sync")

class NodeSync(object):
    """Syncs the local info to the remote server.
    It must receive a NodeInfo instance.
    """

    def __init__(self, nodeinfo):
        self.talk = agent_talk()
        self.nodeinfo = nodeinfo
        self.sync_this = nodeinfo.sync_this
        self.sync_data = nodeinfo.sync_data
        self.store_data = nodeinfo.store_data
        
    def sync_all(self):
        """Send changes to the server and store them in the cache.
        This is the main method and probably the only one needed
        by callers.
        """
        self.setup_session()
        log.info("Done.")
        tables = {'repositories':'',
    #     'task':'', 
         'update_candidates':'',
         'current_packages':'',
          }
        # TODO: nao esta chamando sync_info.. update_candidates
        log.debug("Spool versions: %s" % self.nodeinfo.spool_versions)
        local_versions = tables.copy()
        local_versions.update(self.nodeinfo.spool_versions)

        #remote_versions = {}
        for tbl in local_versions.keys():
            r = self.talk.rpc.get_tbl_version(self.my_session, tbl)
            log.debug("remote tbl version (%s): %d" % (tbl, r))
        #    remote_versions[tbl] =
            if str(local_versions[tbl]) != str(r):
                self.sync_this[tbl] = True
                log.debug("table serial changed (%s)" % tbl)

        # getting tables.keys instead of self.sync_this.keys, because I need to ignore old tables
        for run in tables.keys():
            if run == 'repositories':
                # FIXME, should not ignore repo update
                continue
            if self.sync_this.get(run, False) is True:
                self.sync_info(run)

        # FIXME: Should only sync tasks if remote version differs from locals
        self.sync_task()

    def setup_session(self):
        """Setups server communication
        """
        (uniq, password) = self.talk.auth
        token = hmac.new(password, uniq).hexdigest()
        uname = os.uname()
        os_name = uname[0]
        myhost = uname[1] # Alternative: socket.gethostname()
        os_version = uname[2]

        log.info("Machine identification: %s %s." % (uniq, myhost))
        log.info("Setting up initial session.")

        # Starting server talk
        self.my_session = self.talk.rpc.session_setup(uniq, token)
        # FIXME: Use an exception here
        if not self.my_session:
            log.info("Oops. The server does not know me.")
            add_me = self.talk.rpc.add_computer(password, uniq, myhost, os_name, os_version)
            if add_me:
                log.info("Machine account created on the server.")
            else:
                log.error("Server did not create the account.")
                raise Exception, "Failed to create computer account in the server."
            self.my_session = self.talk.rpc.session_setup(uniq, token)

 
    def sync_rep(self):
        """Syncs repository information.
        This method is doomed.
        """
        #FIXME: there is repeted code here and in sync_info()
        if self.check_diff_rep():
            self.store_tbl_ver('repositories', 'please-update')
            log.info("Storing md5 spool for repositories list.")
            self.store_spool('repositories', [  ['rep_md5','md5',self.rep_md5 ] ], True)
            self.sync_this['repositories'] = True
            log.debug("repositories changed. Must update")

    def sync_info(self,what):
        """Synchronizes information that changed.
        See diff_new_spool(), but diff_list must be a list of two dicts:
            - updated['package'] = version 
            - deleted['package'] = empty
        """
        log.info("Sync %s." % what)
        (updated, deleted) = self.sync_data[what]
        # if the list is *still* empty, ignore it
        if updated.get('empty','') == 'empty':
            return
        # If the list in the cache is new, we must send a full update
        if updated.get(what,'') == 'new':
                # We must wipe the remote info
                log.info("Local cache for '%s' is empty" % what)
                # also, updated will have all data
                ign = self.talk.rpc.wipe_this(self.my_session,what)
        # updating
        ver = self.talk.rpc.set_list_diff(self.my_session, what,
            updated, deleted) 
        # FIXME: this is **WRONG**.
        # we must format the list. see below in blaaa
        self.store_spool(what, self.store_data[what], True)
        self.store_tbl_ver(what, ver)

    def sync_task(self):
        """This operation will *get* new tasks from the server.
        """
        log.info("Getting assigned tasks.")
        get_tasks = self.talk.rpc.get_tasks(self.my_session)
        log.info("Assigned tasks found: " + str(get_tasks) + ".")
        log.debug("Kindly asking server to wipe old tasks.")
        taskver = self.talk.rpc.wipe_this(self.my_session,'tasks')
        self.store_tbl_ver('tasks', taskver)
        store_task = []
        for tas in get_tasks:
           store_task.append(tas)
        if len(store_task) > 0:
            log.debug("Storing tasks in spool.")
            self.store_spool('tasks', store_task)

    def store_tbl_ver(self,tablename, version):
        log.debug("Updating table version: %s - %s" % (tablename, version))
        change_ver = [['tbl_ver', tablename, version]]
        self.store_spool('tbl_ver', change_ver, False)

    def store_spool(self, spool, item_list, wipe_old=False):
        """Stores data in the services pool directory.
        
        It takes a list of itens, each of which contains a list of
        "section", "option" and "value".

        Security is a must here.
        """
        log.debug("Writing spool of type '%s" % spool)
        # FIXME: check for right permissions in the spool dir and files
        spool_path = "/var/spool/nwu/nw.%s" % spool 
        if wipe_old == True:
            try:
                os.unlink(spool_path)
            except:
                pass
            else:
                log.info("Deleted old spool file.")
        store = ConfigParser.ConfigParser()
        r = store.read(spool_path)
    	for it in item_list:
            if type(it) is not list or len(it) < 2:
                raise Exception, "item_list is not right."
            section = it[0]
            option = it[1]
            if len(it) > 2:
                value = it[2]
            else:
                value = 'placeholder'
            if option == '':
                option = 'placeholder'
            log.debug("Found "+ str(section) + ": "+ str(option))
            if not store.has_section(section):
                # create section in the task file
                store.add_section(section)
            store.set(section, option, value)
        try:
            updt_spool = open(spool_path, 'w')
        except:
            log.error("!!! Problem writing to spool directory in " + spool_path + ".")
            pass
        else:
            log.info("Updating spool file for " + spool + ".")
            store.write(updt_spool)

