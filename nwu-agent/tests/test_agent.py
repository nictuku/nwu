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
HDLR = logging.StreamHandler()
log.addHandler(HDLR)
log.setLevel(logging.DEBUG)

# setup
NEW = ''
EMPTY = """[update_candidates]
empty = empty
"""

VALID = """[cur_pkgs]
scim-gtk2-immodule = 1.4.4-1ubuntu12
python-twisted-conch = 1:0.6.0-5ubuntu1
ttf-lao = 0.0.20060226-1build1
xserver-xorg-driver-tseng = 1:1.0.0.5-0ubuntu1
"""

VALID_DICT = {'scim-gtk2-immodule': '1.4.4-1ubuntu12', 
            'xserver-xorg-driver-tseng': '1:1.0.0.5-0ubuntu1', 
            'python-twisted-conch': '1:0.6.0-5ubuntu1', 
            'ttf-lao': '0.0.20060226-1build1'
            } 

class NewNodeInfo(node_info.NodeInfo):
    """NodeInfo class with some methods overloaded to allow testings
    """
    def __init__(self):
        self.cksum_cache = {}
        self.cksum_curr = {} 
        self.store_data = {} 
        self.full_data = {} 

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
        
NWU_MAINT = nwu_agent.maint
TEST_NODE_INFO = NewNodeInfo()

class TestMe(unittest.TestCase):

    TEST_NODE_INFO.stream = StringIO(VALID)
 
    def test_read_spool(self):
  
        assert TEST_NODE_INFO.read_spool('update_candidates',  StringIO(NEW))\
 == {'update_candidates': 'new' }

        assert TEST_NODE_INFO.read_spool('update_candidates', StringIO(EMPTY))\
 == {'empty':'empty'}
 
        assert TEST_NODE_INFO.read_spool('update_candidates', StringIO(VALID))\
 == VALID_DICT 

    def test_diff_dicts(self):
        dict1 = {'A' : 123, 'B': '....', 'C': False }
        dict2 = {'A' : 123, 'B': '....', 'C': False }
        assert TEST_NODE_INFO.diff_dicts(dict1, dict2) == ({}, {})
        dict2 = {}
        assert TEST_NODE_INFO.diff_dicts(dict1, dict2) == ({}, dict1)
        assert TEST_NODE_INFO.diff_dicts(dict2, dict1) == (dict1, {})
        assert TEST_NODE_INFO.diff_dicts({}, {}) == ({}, {})    

    def test_apt_get(self):
        self.assertRaises(Exception, "NWU_MAINT.apt_get('BLA')") 
        self.assertRaises(Exception, 
            "NWU_MAINT.apt_get('install', packages='')")
        self.assertRaises(Exception, 
            "NWU_MAINT.apt_get('install', packages=[])")
        self.assertRaises(Exception, "NWU_MAINT.apt_get('install')")
        assert NWU_MAINT.apt_get('install', packages=['foo'] ) == ('apt-get', 
            ['install', 'foo'])
        assert NWU_MAINT.apt_get('update' ) == ('apt-get', ['update'])
        assert NWU_MAINT.apt_get('upgrade', packages=['foo'] ) == ('apt-get', 
            ['upgrade'])
        assert NWU_MAINT.apt_get('install', packages=['foo'], 
            assume_yes=True ) == ('apt-get', 
            [ '--assume-yes', 'install', 'foo'])
        assert NWU_MAINT.apt_get('upgrade', packages=['foo', 'bar'], \
allow_unauthenticated=True, assume_yes=True ) == \
            ('apt-get', ['--assume-yes', '--allow-unauthenticated', 
            'upgrade'])

    def test_is_safe(self):
        assert NWU_MAINT.is_safe('xx:') == False
        assert NWU_MAINT.is_safe('`') == False
        assert NWU_MAINT.is_safe("'") == False
        assert NWU_MAINT.is_safe('"') == False
        assert NWU_MAINT.is_safe('12._') == True
        assert NWU_MAINT.is_safe('xx:', True) == True

    def test_rep_valid(self):
        assert NWU_MAINT.rep_valid('deb') == False
        assert NWU_MAINT.rep_valid('deb incomplete') == False
        assert NWU_MAINT.rep_valid('deb-invalid url component') == False
        assert NWU_MAINT.rep_valid('deb http://bla.com ./') == True
        assert NWU_MAINT.rep_valid('deb-src http://bla.com distro component1 \
component2') == True

    def test_changes(self):
        update_candidates =  { 
            'python-glade2' : '2.12.0-0ubuntu2',
            'python-gmenu' : '2.20.1-0ubuntu1',
            'python-gnome2' : '2.20.0-0ubuntu1',
            'xserver-xorg-driver-tseng': '1:1.0.0.5-0ubuntu1', 
            }

        TEST_NODE_INFO.info = { 
            'update_candidates' : update_candidates
        }
        diff_spool = TEST_NODE_INFO.diff_new_spool('update_candidates')
        log.debug("cached: %s" % str(diff_spool[0]))
        log.debug("current: %s" % str(diff_spool[1]))
        log.debug("diff: %s" % str(diff_spool[2]))
        assert diff_spool[0] == VALID_DICT
        assert diff_spool[1] == update_candidates
        assert diff_spool[2] == (
            { 'python-gnome2': '2.20.0-0ubuntu1',
            'python-glade2': '2.12.0-0ubuntu2', 
            'python-gmenu': '2.20.1-0ubuntu1' }, 
            { 'scim-gtk2-immodule': '1.4.4-1ubuntu12', 
            'python-twisted-conch': '1:0.6.0-5ubuntu1', 
            'ttf-lao': '0.0.20060226-1build1'}
            )

        # testing get_changes
        try:
            TEST_NODE_INFO.full_data['update_candidates']
        except KeyError:
            pass
        else:
            self.fail("Expected an AttributeError")
        TEST_NODE_INFO.get_changes('update_candidates')
        # FIXME: broken test. continue from here
        # assert TEST_NODE_INFO.full_data['update_candidates'] == 'BROKEN'
 
