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

import sys
sys.path.append('.')

import nwu_agent
import nwu_agent.misc

class TestAgent:
 
    def setup_method(self, method):
        pass 

    def test_diff_dicts(self):
        old_dict = {'A' : 123, 'B': '....', 'C': False }
        new_dict = {'A' : 123, 'B': '....', 'C': False }
        assert nwu_agent.misc.diff_dicts(old_dict, new_dict) == {}

    def istrue(self, a, b):
        return True
