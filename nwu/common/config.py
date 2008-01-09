#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2008 Yves Junqueira (yves@cetico.org)
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

from ConfigParser import SafeConfigParser
import sys
from os import path

class Config(SafeConfigParser):
    def __init__(self, filename):
        self.filename = path.expanduser(filename)
        self.fp = None
        SafeConfigParser.__init__(self)

        self.read()

    def read(self):
        try:
            self.fp = open(self.filename, 'r')
            self.readfp(self.fp)
            self.fp.close()
        except IOError, e:
            # XXX: Do we really want to print this warning? If so, is the 
            #      formatting okay?
            print '[WARNING] %s' % (e)
            print '          No config file found; using built-in default settings!'

    def get(self, section, option, default=''):
        if not self.has_section(section) \
                or not self.has_option(section, option):
            return default

        return SafeConfigParser.get(self, section, option)

    def items(self, section):
        if not self.has_section(section):
            return []
        return SafeConfigParser.items(self, section)
