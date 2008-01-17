#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006,2007,2008 Yves Junqueira (yves@cetico.org)
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

VERSION='0.1.7-dev'

def is_safe(str, http=False):
    # Moved here from nwu.server.cli/nwu.
    # From Byron Ellacot's message in the mod_python list     
    # http://www.modpython.org/pipermail/mod_python/2004-December/016987.html  

    ok_chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_"

    # We can also selectively accept other chars
    if http:
        ok_chars += "/: "

    return [x for x in str if x.lower() not in ok_chars] == []
