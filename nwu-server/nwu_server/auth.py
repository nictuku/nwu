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


from db.operation import *
import hmac

def check_token(uniq, token):
    """Checks if the specified token was generated using the stored
    machine password.
    """

    query_check_t = machine.select(machine.q.uniq==uniq)
    check_t = list(query_check_t)

    password = ''

    if len(check_t) == 0:
        # No machine with that specified uniq id was found.
        return False
    else:
        for t in check_t:
            password = t.password

    valid_token = hmac.new(password, uniq).hexdigest()

    if valid_token == token:
        # Yeah, this is a valid token!
        return True


