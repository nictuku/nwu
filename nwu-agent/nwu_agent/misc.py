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

import os
import logging
#from xml.sax.saxutils import escape as xmlescape
import re
import sysinfo
import string
import random
import stat
import ConfigParser
from M2Crypto import SSL
from M2Crypto.m2xmlrpclib import Server, SSL_Transport
import logging
import sys
from md5 import md5 

log = logging.getLogger('nwu_agent.misc')

class agent_talk:

    def __init__(self, load_config=True):
        if load_config:
            self.conffile = '/etc/nwu/agent.conf'
            config = ConfigParser.ConfigParser()

            if not os.access(self.conffile, os.R_OK):
                log.error("Config file " + self.conffile + " is not readable by the current user.")
                sys.exit(1)

            r = config.read("/etc/nwu/agent.conf")

            self.server_uri = config.get("connection", "server_uri")

            # grr I don't want to have to do this. Fix sysinfo
            format = "%(asctime)s cacic[%(process)d] %(levelname)s %(name)s:%(lineno)d: %(message)s"
            sysinfo_logger = logging.getLogger("sysinfo")
            sysinfo_logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(format)
            ch.setFormatter(formatter)
            sysinfo_logger.addHandler(ch)

            #Config.simplify_objects = 1 
            sourcefiles = self.list_sources_list()
            self.repositories, self.rep_md5 = self.read_sources_list(sourcefiles)
            self.pkgs = sysinfo.software.packages()
            self.packages = self.pkgs.installed_ver
            self.update_candidates = self.pkgs.update_candidates
            self.rpc = self.XClient(self.server_uri)
            

    def verify(self, conn, cert, errnum, depth, ok):
        print 'So-far =',ok
        print 'errno =',errnum
        print 'conn =',conn
        print 'oi', cert.get_issuer()
        print '    Subject: ', cert.get_subject()
        print "ok"
        print '        O     : %s' % cert.get_subject().O
        print '        OU    : %s' % cert.get_subject().OU
        print '        CN    : %s' % cert.get_subject().CN
        print '        email : %s' % cert.get_subject().emailAddress
        print '    Serial : %s' % cert.get_serial_number()
        print '    SHash  : %s' % cert.subject_name_hash()
        print '   Expired : %s' % cert.has_expired()
        print '   CN : %s' % cert
        return ok

    def XClient(self, server_uri):
        ctx = SSL.Context('sslv3')
        #ctx.load_cert_chain('/tmp/server.pem')
        ctx.set_allow_unknown_ca(1)
    #    ctx.load_cert('/tmp/server.pem')
    #    ctx.load_verify_info('/tmp/cacert.pem')
    #    ctx.load_client_ca('/tmp/cacert.pem')
        #print "ve1"
        #ctx.set_verify(SSL.verify_peer, 10)
        #print "ve2"
        xs = Server(server_uri, SSL_Transport(ctx))
        return xs


    def get_auth(self):
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

        # dump changes
        if changed:
            log.info("Storing auth settings to " + auth_path)
            auth_fd = open(auth_path, 'w')
            auth_file.write(auth_fd)
            auth_fd.close()

        session = uniq, password

        return session

     
#    def get_current(self, info):
#        #get_packages()
#        if info == 'pkgs':
#            packages = self.pkgs.installed_ver
#            return packages
#        elif info == 'update_candidates':
#            update_candidates = self.pkgs.update_candidates
#            return update_candidates    
            
      
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

        if category not in ['packages', 'update_candidates', 'tbl_ver', 
            'repositories']:
            raise Exception, "Wrong cache category specified: " + category

        if not stream:
            cache_path = "/var/spool/nwu/nw." + category
            stream = open(cache_path)

        cache = ConfigParser.ConfigParser()
        result = cache.readfp(stream)

        #if len(result) < 1:
        #    log.error("Could not read " + category + " cache")
        #    return {category:'empty'} 
        
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
        current = eval('self.' + info)
        print "cache:", cached
        print "current:", current
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

    def store_spool(self, spool, item_list, wipe_old=False):
        """Stores data in the services pool directory.
        
        It takes a list of itens, each of which contains a list of
        "section", "option" and "value".

        Security is a must here."""
        # FIXME: check for right permissions in the spool dir and files

        spool_path = "/var/spool/nwu/nw." + spool 

        if wipe_old == True:
            try:
                os.unlink(spool_path)
            except:
                pass
            else:
                log.info("Deleted old spool file.")

        store = ConfigParser.ConfigParser()

        r = store.read(spool_path)
        print "item list", item_list, spool
    	for it in item_list:
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

