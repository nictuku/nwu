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

"""Actions run by root from nwu-maint are defined here. It has to be 100%
safe.
"""
import logging

log = logging.getLogger('nwu-maint.agent.maint')

def is_safe(str, http=False):
    # From Byron Ellacot's message in the mod_python list
    # http://www.modpython.org/pipermail/mod_python/2004-December/016987.html

    OK_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789.-_"

    # We can also selectively accept other chars

    if http:
        OK_CHARS += "/: "

    return [x for x in str if x.lower() not in OK_CHARS] == []

def repadd(newrep):
    """Add a new repository to the sources.list file.
    newrep is a dictionary with "type", "uri", "distribution" and "components" keys.
    """

    if is_safe(rep_string):
        print "New rep is safe: " + rep_string 
