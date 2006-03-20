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

"""Configures database access
"""

import logging
import ConfigParser
from sqlobject import *

log = logging.getLogger('nwu_server.db.setup')

class cfg:
    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read("/etc/nwu/server.conf")

        db_type = config.get("database", "type")
        db_host = config.get("database", "host")
        db_database = config.get("database", "database")
        db_user = config.get("database", "user")
        db_password = config.get("database", "password")


        log.debug("Using" + db_type + " as my database.")

        if db_type == 'sqlite':
            connection_string = db_type + "://" + db_database
        else:
            connection_string = db_type + "://" + db_user + ":" + db_password + "@" +\
             db_host + "/" + db_database

        log.debug("conn string:" + connection_string)
        self.conn = connectionForURI(connection_string)

        self.conn.debug=0

if __name__ == '__main__':
    print cfg().conn
