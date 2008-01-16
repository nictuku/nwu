#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2008 Stephan Peijnik (sp@gnu.org)
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

from gzip import GzipFile

class Package:
    """ Package representation. """
    def __init__(self, name):
        self.name = name
        self.values = {}

    def set(self, name, value):
        self.values[name] = value

    def get(self, name):
        if not name in self.values:
            return None
        return self.values[name]

    def __repr__(self):
        return '<Package: %s>' % (self.name)
    
    def __str__(self):
        return self.name

class PackagesFile:
    """ Packages file parser. 

    This class provides a parser for apt Packages and Packages.gz files.
    NOTE: This class needs to be extended and the add_package method needs
          to be overridden.
    """
    def __init__(self, fileName, gzipped=False):
        """ Initializes parser.

        If gzipped is True GzipFile is used to read the file instead of open.
        """
        self.fileName = fileName
        self.gzipped = gzipped
        self.curPkg = None
    
    def read(self):
        """ Reads Packages file. 

        NOTE: This method may raise an IOError if reading fails or an Exception
              if there is something wrong with the format of the Packages file.
        """
        fp = None

        if not self.gzipped:
            fp = open(self.fileName, 'r')
        else:
            fp = GzipFile(self.fileName, 'r')

        for line in fp.readlines():
            self.process_line(line.strip())
        fp.close()

    def process_line(self, line):
        """ Processes line.

        NOTE: This method may raise an Exception if there is something wrong
              with the format of the Packages file.
        """
        if len(line) == 0 or line[0] == ' ':
            return

        try:
            hdr_name, hdr_value = line.split(':', 1)
        except:
            return

        hdr_value = hdr_value.strip()

        if hdr_name == 'Description':
            # Ignore Description for now.
            return

        elif hdr_name == 'Package':
            if self.curPkg:
                self.add_package(self.curPkg)

            self.curPkg = Package(hdr_value)
        else:
            if not self.curPkg:
                raise Exception('Invalid Packages file.')
            self.curPkg.set(hdr_name, hdr_value)
    
    def add_package(self, package):
        """ "Adds" a package.

        This method has to be overridden. Place code to store the data
        gathered about a package here.
        """
        raise Exception('add_package() needs to be implemented by subclass')
