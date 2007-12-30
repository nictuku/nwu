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

import ConfigParser
import re
from md5 import md5
import sysinfo
import logging

log = logging.getLogger('nwu_agent.node_info')

class NodeInfo(object):
    """Gets all needed info that will be sync'ed to the server
    No sync operation is done here.
    """
    def __init__(self):
        self.sync_this = {}
        self.sync_data = {}
        self.store_data = {}
        self.cksum_data = {}
        sourcefiles = self.list_sources_list()
        self.repositories, self.rep_md5 = self.read_sources_list(
                sourcefiles)
        self.pkgs = sysinfo.software.packages()
        self.info = { 'current_packages' : self.pkgs.installed_ver,
            'update_candidates' : self.pkgs.update_candidates,
            'repositories' : self.repositories 
            }
        self.get_all_news()
        self.spool_versions = self.read_spool('tbl_ver')
        
    def get_all_news(self):
        """See what info has changed in the system
        Sets sync_data and sync_this approprietly
        """
        check_me = ['update_candidates', 'current_packages']
        for check in check_me:
            diff = self.get_changes(check)
            for operation in diff:
                self.sync_data[check] = diff
                if len(operation) > 0:
                    self.sync_this[check] = True
                    break

    def get_changes(self,where='current_packages'):
        """
        Process the diff between current system information and
        the data cached in /var/spool/nwu and returns the
        diff data if any, or None.

        'where' can be:
        - current_packages
        - update_candidates
        """
        [cached_pkgs, current_pkgs, diff_pkgs] = self.diff_new_spool(where)
        my_list = []
        cksum_tmp = ''
        keys = current_pkgs.keys()
        keys.sort()
        for key in keys:
            val = current_pkgs[key]
            my_list.append([where, key, val])
            cksum_tmp += key + val + ' '
        self.cksum_data[where] = md5(cksum_tmp).hexdigest()
        self.store_data[where] = my_list
        log.debug("Formatting changes for %s." % where)
#        log.debug("cur: %s " % repr(current_pkgs))
#        log.debug("cac: %s " % repr(cached_pkgs))
#        log.debug("dif: %s " % repr(diff_pkgs))
        return diff_pkgs

    def list_sources_list(self):
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
    def read_sources_list(self, filenames):
        full_string = ''
        repositories = []
        for source in filenames:
            # any use to handle exceptions here?
            f = open(source, 'r')
            thisrep = [source]
            for line in f:
                full_string += line
                line = line.strip()
                #ignore comments and blank lines
                l = line.split('#',1)[0]
                ignore = re.search(r'^$|#|^\s+$', l)
                if not ignore :
                    thisrep.append(l)
        #pik = pickle.dumps(repositories)
            repositories.append(thisrep)
        return repositories, md5(full_string).hexdigest()

    def diff_dicts(self, old_dict, new_dict):
        """This function detects the differences between two dicts,
        returning two dicts: new or changed keys; and deleted keys
        """
        updated_keys = [ k for k in new_dict if k not in old_dict
            or new_dict[k] != old_dict[k] ]
        up_k = {}
        for k in updated_keys:
            up_k[k] = new_dict[k]
        deleted_keys = [ k for k in old_dict if k not in new_dict ]
        del_k = {}
        for k in deleted_keys:
            del_k[k] = old_dict[k]
        return (up_k, del_k)

    def read_spool(self, category, stream=None):

        if category not in ['current_packages', 'update_candidates', 'tbl_ver',
            'repositories']:
            raise Exception, "Wrong cache category specified: " + category
        if not stream:
            cache_path = "/var/spool/nwu/nw.%s" % category
            try:
                stream = open(cache_path, 'r')
            except IOError:
                log.debug("%s spool file not found." % category)
                return {category:'new'}
        cache = ConfigParser.ConfigParser()
        result = cache.readfp(stream)
        objects = {}
        if len(cache.sections()) < 1:
             return {category:'new'}
        for s in cache.sections():
            for option, value in cache.items(s):
                objects[option] = value
        return objects

    def diff_new_spool(self, info):
        """Returns a list of:
        - cached info
        - current info
        - diff of previous both [updated, deleted]
        """
        cached = self.read_spool(info)
        current = self.info[info]
        diff = self.diff_dicts(cached, current)
        return [cached, current, diff]

    def check_diff_rep(self):
        """Checks if the new repositories list
        is new or not.
        """
        cached = self.read_spool('repositories').get('md5','')
        current = self.rep_md5
        if cached != current:
            return True
        else:
            return False
