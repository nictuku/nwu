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
import ConfigParser
import logging
log = logging.getLogger('nwu_server.config')

def read_config(config_path):
    """Reads configuration data from the config file.
    """
    config_p = ConfigParser.ConfigParser()
    config_p.read(config_path)

    host = config_p.get("webservice", "host").lower()
    port = int(config_p.get("webservice", "port"))
    # FIXME: make pemfile configurable, but use a 'default' value 
    # (requires a special ConfigParser)
    #pemfile = config_p.get("webservice", "pemfile")
    pemfile = '/etc/nwu/server.pem'
    db_type = config_p.get("database", "type")
    db_host = config_p.get("database", "host")
    db_database = config_p.get("database", "database")
    db_user = config_p.get("database", "user")
    db_password = config_p.get("database", "password")
    log.info("db: Using " + db_type + " as database backend.")
    connection_string = db_type + "://" + db_user + ":" + \
       db_password + "@" + db_host + "/" + db_database 

    config = { 'host' : host, 
    'port' : port, 
    'pemfile' : pemfile,
    'databasetype' : db_type,
    'connection_string' : connection_string,
    }
    return config
