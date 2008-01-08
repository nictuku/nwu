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

"""Reads and parses the configuration for nwu-server
"""
# Make use of new config parser.
#
# XXX: Can we completly get rid of this module? We could use nwu.common.config
#      directly.
from nwu.common.config import Config
import logging
log = logging.getLogger('nwu.server.config')

def read_config(config_path):
    """Reads configuration data from the config file.
    """
    config_p = Config(config_path)

    host = config_p.get("webservice", "host", "localhost").lower()
    port = int(config_p.get("webservice", "port", 8088))
    pemfile = config_p.get("webservice", "pemfile", "/etc/nwu/server.pem")
    cacert = config_p.get("webservice", "cacert", "/etc/nwu/ca.crt")
    db_type = config_p.get("database", "type", "sqlite")
    db_host = config_p.get("database", "host")
    db_database = config_p.get("database", "database", "/var/lib/nwu/nwu.db")
    db_user = config_p.get("database", "user")
    db_password = config_p.get("database", "password")
    log.info("db: Using " + db_type + " as database backend.")
    connection_string = db_type + "://" + db_user + ":" + \
       db_password + "@" + db_host + "/" + db_database 

    config = { 'host' : host, 
    'port' : port, 
    'pemfile' : pemfile,
    'cacert': cacert,
    'databasetype' : db_type,
    'connection_string' : connection_string,
    }
    return config
