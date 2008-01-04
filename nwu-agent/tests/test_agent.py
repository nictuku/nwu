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

import nwu_agent
from nwu_agent import node_info
import nwu_agent.talk
import nwu_agent.maint

import unittest

agent = nwu_agent.talk.agent_talk(load_config=False)
m = nwu_agent.maint
i = node_info.NodeInfo()

class TestAgent(unittest.TestCase):
 
    def setup_method(self, method):
        pass 

    def test_read_update_candidates_spool(self):
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
   
        assert i.read_spool('update_candidates',  StringIO(new)) == \
            {'update_candidates': 'new' }

        assert i.read_spool('update_candidates', StringIO(empty)) == \
            {'empty':'empty'}
 
        assert i.read_spool('update_candidates', StringIO(valid)) == \
            {'scim-gtk2-immodule': '1.4.4-1ubuntu12', 
            'xserver-xorg-driver-tseng': '1:1.0.0.5-0ubuntu1', 
            'python-twisted-conch': '1:0.6.0-5ubuntu1', 
            'ttf-lao': '0.0.20060226-1build1'
            }

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
            ('apt-get', ['--assume-yes', '--allow_unauthenticated', 'upgrade'])

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

