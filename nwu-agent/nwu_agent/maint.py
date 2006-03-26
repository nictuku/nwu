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

def rep_valid(repository):
    """Validate repository string
    """

    # FIXME: use a validational regexp

    if not is_safe(repository,http=True):
        log.warn("Ignoring repository: strange characters")
        return False
    
    rep_elements = repository.split()
    if len(rep_elements) < 3:
        log.warn("Ignoring repository: missing elements")
        return False

    rep_type = rep_elements[0]
    rep_uri = rep_elements[1]
    rep_distribution = rep_elements[2]
    rep_components = " ".join(rep_elements[3:])

    valid_types = ['deb', 'deb-src']

    if not rep_type in valid_types:
        log.warn("Ignoring repository: rep-type not valid")
        return False
    
    return True

def rep_add(newrep):
    """Add a new repository to the sources.list file.
    newrep is a dictionary with "type", "uri", "distribution" and "components" keys.
    """

    if rep_valid(newrep):
                
        # Write to sources.list
        # FIXME: if apt version support, we could use /etc/apt/sources.list.ld
        log.info("Writing new repository to sources.list")
        src = open('/etc/apt/sources.list', 'a')
        src.write("\n" + newrep + "\n")
        return True

    else:
        return False
