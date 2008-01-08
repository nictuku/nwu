#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006-2008 Yves Junqueira (yves@cetico.org)
#
#    This file is part of NWU.
#
#    NWU is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    NWU is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with NWU.  If not, see <http://www.gnu.org/licenses/>.

import hmac
import logging
import os

from nwu.common.config import Config
from nwu.agent.talk import agent_talk

log = logging.getLogger("nwu.agent.node_sync")

class NodeSync(object):
    """Syncs the local info to the remote server.
    Note that it must be called with a NodeInfo instance.
    """

    def __init__(self, nodeinfo):
        self.talk = agent_talk()
        self.nodeinfo = nodeinfo
        self.store_data = nodeinfo.store_data
        self.mark_sync_full = {}
        self.mark_sync_diff = {}
        
    def sync_all(self):
        """Send changes to the server and store them in the cache.
        This is the main method and probably the only one needed
        by callers.

        It's a very crucial part of the system, because this function
        decides what should be sync'ed to the server and how (full, diff,
        etc).
        
        = components =
        - A) the client "real" data (as read from python-sysinfo) 
        - B) the client current 'local cache' (which normally represents what 
        the client *thinks* the server knows) 
        - C) the data about this client currently stored at the database 
        by the server

        So on every sync, they must be compared based on checksum 
        (possible drawback: more CPU usage)

        if C == B == A: do nothing

        if ( C == B ) && (C != A): client data changed. send diff of changes

        unlikely:

        if C != B: "server wiped database?" - full sync

        if C, B, A are different - full sync

        if B is empty: "wiped or new" - full sync 
        """

        # A = self.nodeinfo.cksum_curr[tbl]
        # B = self.nodeinfo.cksum_cache[tbl]
        # C = server_ver (see below)

        self.setup_session()

        # FIXME: keep this somewhere else. there are duplicates around
        tables = {

        # not being updated
        # 'repositories':'',
        # always being updated
        # 'tasks':'', 
             'update_candidates':'',
             'current_packages':'',
          }

        for tbl in tables.keys():
            # get A and B
            self.nodeinfo.get_changes(tbl)
            log.debug("sync_all: cksum_curr (%s): %s" % (tbl, self.nodeinfo.cksum_curr.get(tbl,'-')))
            log.debug("sync_all: cksum_cache (%s): %s" % (tbl, self.nodeinfo.cksum_cache.get(tbl, '-')))
            # get "C" from the server (see above)
            server_ver = self.talk.rpc.get_tbl_cksum(self.my_session, tbl)
            log.debug("sync_all: server_ver (%s): %s" % (tbl, server_ver))
            if not self.nodeinfo.cksum_curr.has_key(tbl):
                log.warn("sync_all: no cksum_curr found for %s. Skipping." % tbl)
                continue
            elif not self.nodeinfo.cksum_cache.has_key(tbl):
                log.warn("sync_all: no cksum_cache found for %s. \
This is not normal, so marking for full sync..." % tbl )
                self.mark_sync_full[tbl] = True
            elif self.nodeinfo.cksum_cache == '':
                log.debug("sync_all: empty cache (%s). Marking for full sync." % tbl)
                self.mark_sync_full[tbl] = True
                continue
            elif self.nodeinfo.cksum_cache[tbl] != str(server_ver):
                log.info("sync_all: local cache and server cache mismatch \
(%s)!! Marking for full sync" % tbl)
                self.mark_sync_full[tbl] = True
            elif  self.nodeinfo.cksum_curr[tbl] != str(server_ver):
                log.debug("sync_all: server and curr cksum mismatch (%s). \
Marking for diff sync" % tbl)
                self.mark_sync_diff[tbl] = True
            elif self.nodeinfo.cksum_curr[tbl] != self.nodeinfo.cksum_cache[tbl]:
                log.debug("sync_all: local cache not current (%s). \
Marking for diff sync." % tbl)
                self.mark_sync_diff[tbl] = True
                
        # getting tables.keys instead of self.sync_this.keys, because I need
        # to ignore old tables
        for run in tables.keys():
            if self.mark_sync_full.get(run, False) is True:
                self.sync_info(run, True)
            elif self.mark_sync_diff.get(run, False) is True:
                self.sync_info(run, False)

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
        log.debug("setup_session: done")
 
    def sync_rep(self):
        """Syncs repository information.
        This method is doomed.
        """
        #FIXME: there is repeted code here and in sync_info()
        if self.check_diff_rep():
            log.info("Storing md5 spool for repositories list.")
            self.store_spool('repositories', [  ['rep_md5','md5',self.rep_md5 ] ], True)
            self.sync_this['repositories'] = True
            log.debug("repositories changed. Must update")

    def sync_info(self,what,is_full_sync):
        """Synchronizes information that changed.
        See diff_new_spool(), but diff_list must be a list of two dicts:
            - updated['package'] = version 
            - deleted['package'] = empty
        """
        if is_full_sync:
            mode = 'FULL'
        else:
            mode = 'DIFF'
        log.info("Syncing %s (%s)." % (what, mode))

        if is_full_sync:
            ign = self.talk.rpc.wipe_this(self.my_session,what)
            updated = self.nodeinfo.full_data[what][1]
            deleted = {}
        else:
            (updated, deleted) = self.nodeinfo.full_data[what][2]

        log.debug("updated: %s" % updated)
        log.debug("deleted: %s" % deleted)
        # updating
        ver = self.talk.rpc.set_list_diff(self.my_session, what,
            updated, deleted) 
        # FIXME: this is **WRONG**.
        # we must format the list. see below in blaaa
        self.store_spool(what, self.store_data[what], True)

    def sync_task(self):
        """This operation will *get* new tasks from the server.
        """
        log.info("Getting assigned tasks.")
        get_tasks = self.talk.rpc.get_tasks(self.my_session)
        log.info("Assigned tasks found: " + str(get_tasks) + ".")
        log.debug("Kindly asking server to wipe old tasks.")
        taskver = self.talk.rpc.wipe_this(self.my_session,'tasks')
        store_task = []
        for tas in get_tasks:
           store_task.append(tas)
        if len(store_task) > 0:
            log.debug("Storing tasks in spool.")
            self.store_spool('tasks', store_task)

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
        store = Config(spool_path)

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
            # XXX: What happens with updt_spool here? Looks unused.
            #      Either way, udpt_spool.close() might be missing here.
        except:
            log.error("!!! Problem writing to spool directory in " + spool_path + ".")
            pass
        else:
            log.info("Updating spool file for " + spool + ".")
            store.write(updt_spool)
            # XXX: Are we missing updt_spool.close() here?

