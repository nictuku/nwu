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


# unittest-compatible tests
# callable using 'nosetests'

from StringIO import StringIO
import sys
sys.path.append('.')
import ConfigParser

import nwu_agent
from nwu_agent import node_info
import nwu_agent.talk
import nwu_agent.maint

import unittest
import logging

log = logging.getLogger()
hdlr = logging.StreamHandler()
log.addHandler(hdlr)
log.setLevel(logging.DEBUG)

# setup
new = ''
empty = """[update_candidates]
empty = empty
"""

valid = """[cur_pkgs]
scim-gtk2-immodule = 1.4.4-1ubuntu12
python-twisted-conch = 1:0.6.0-5ubuntu1
ttf-lao = 0.0.20060226-1build1
xserver-xorg-driver-tseng = 1:1.0.0.5-0ubuntu1
"""

valid_dict = {'scim-gtk2-immodule': '1.4.4-1ubuntu12', 
            'xserver-xorg-driver-tseng': '1:1.0.0.5-0ubuntu1', 
            'python-twisted-conch': '1:0.6.0-5ubuntu1', 
            'ttf-lao': '0.0.20060226-1build1'
            } 

class TestNodeInfo(node_info.NodeInfo):
    """NodeInfo class with some methods overloaded to allow testings
    """
    def __init__(self):
        pass

    def read_spool(self, category, stream=None):
        """Read spool always in "stream mode"

        If no 'stream' is provided, read "self.stream"
        """
        if category not in ['current_packages', 'update_candidates',
            'repositories']:
            raise Exception, "Wrong cache category specified: " + category
        cache = ConfigParser.ConfigParser()
        if not stream:
            stream = self.stream
        result = cache.readfp(stream)
        objects = {}
        if len(cache.sections()) < 1:
             return {category:'new'}
        for s in cache.sections():
            for option, value in cache.items(s):
                objects[option] = value
        return objects

## run the tests
        
agent = nwu_agent.talk.agent_talk(load_config=False)
m = nwu_agent.maint
i = TestNodeInfo()

class TestMe(unittest.TestCase):
 
    def test_diff_new_spool(self):
        i.stream = StringIO(valid)
        update_candidates =  { 
            'python-glade2' : '2.12.0-0ubuntu2',
            'python-gmenu' : '2.20.1-0ubuntu1',
            'python-gnome2' : '2.20.0-0ubuntu1',
            'xserver-xorg-driver-tseng': '1:1.0.0.5-0ubuntu1', 
            }

        i.info = { 
            'update_candidates' : update_candidates
        }
        diff_spool = i.diff_new_spool('update_candidates')
        log.debug("cached: %s" % str(diff_spool[0]))
        log.debug("current: %s" % str(diff_spool[1]))
        log.debug("diff: %s" % str(diff_spool[2]))
        assert diff_spool[0] == valid_dict
        assert diff_spool[1] == update_candidates
        assert diff_spool[2] == (
            { 'python-gnome2': '2.20.0-0ubuntu1',
            'python-glade2': '2.12.0-0ubuntu2', 
            'python-gmenu': '2.20.1-0ubuntu1' }, 
            { 'scim-gtk2-immodule': '1.4.4-1ubuntu12', 
            'python-twisted-conch': '1:0.6.0-5ubuntu1', 
            'ttf-lao': '0.0.20060226-1build1'}
            )
 
    def test_read_spool(self):
  
        assert i.read_spool('update_candidates',  StringIO(new)) == \
            {'update_candidates': 'new' }

        assert i.read_spool('update_candidates', StringIO(empty)) == \
            {'empty':'empty'}
 
        assert i.read_spool('update_candidates', StringIO(valid)) == \
            valid_dict 

    def test_diff_dicts(self):
        dict1 = {'A' : 123, 'B': '....', 'C': False }
        dict2 = {'A' : 123, 'B': '....', 'C': False }
        assert i.diff_dicts(dict1, dict2) == ({},{})
        dict2 = {}
        assert i.diff_dicts(dict1, dict2) == ({}, dict1)
        assert i.diff_dicts(dict2, dict1) == (dict1, {})
        assert i.diff_dicts({}, {}) == ({}, {})    

    def test_apt_get(self):
        self.assertRaises(Exception, "m.apt_get('BLA')") 
        self.assertRaises(Exception, "m.apt_get('install', packages='')")
        self.assertRaises(Exception, "m.apt_get('install', packages=[])")
        self.assertRaises(Exception, "m.apt_get('install')")
        assert m.apt_get('install', packages=['foo'] ) == ('apt-get', ['install', 'foo'])
        assert m.apt_get('update' ) == ('apt-get', ['update'])
        assert m.apt_get('upgrade', packages=['foo'] ) == ('apt-get', ['upgrade'])
        assert m.apt_get('install', packages=['foo'], assume_yes=True ) == ('apt-get', [ '--assume-yes', 'install', 'foo'])
        assert m.apt_get('upgrade', packages=['foo', 'bar'], allow_unauthenticated=True, assume_yes=True ) == \
            ('apt-get', ['--assume-yes', '--allow-unauthenticated', 'upgrade'])

    def test_is_safe(self):
        assert m.is_safe('xx:') == False
        assert m.is_safe('`') == False
        assert m.is_safe("'") == False
        assert m.is_safe('"') == False
        assert m.is_safe('12._') == True
        assert m.is_safe('xx:', True) == True

    def test_rep_valid(self):
        assert m.rep_valid('deb') == False
        assert m.rep_valid('deb incomplete') == False
        assert m.rep_valid('deb-invalid url component') == False
        assert m.rep_valid('deb http://bla.com ./') == True
        assert m.rep_valid('deb-src http://bla.com distro component1 component2') == True

