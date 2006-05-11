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
from sqlobject.dbconnection import ConnectionURIOpener, TheURIOpener
try:
    from sqlobject.dbconnection import ConnectionHub
except ImportError:
    from backport import ConnectionHub

log = logging.getLogger('nwu_server.db.setup')

hub_registry = set()

cfg = None

class read_conf:
    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read("/etc/nwu/server.conf")

        db_type = config.get("database", "type")
        db_host = config.get("database", "host")
        db_database = config.get("database", "database")
        db_user = config.get("database", "user")
        db_password = config.get("database", "password")

        log.info("Using" + db_type + " as my database.")

        if db_type == 'sqlite':
            self.connection_string = db_type + "://" + db_database + \
               '?cache=True'
        else:
            self.connection_string = db_type + "://" + db_user + ":" + \
               db_password + "@" + db_host + "/" + db_database + '?cache=True'

class AutoConnectHub(ConnectionHub):
    """Connects to the database once per thread."""
    # Based on turbogear's code, without transaction support, though.
    uri = None
    params = {}

    def __init__(self, uri=None):
        if not uri:
            global cfg
            cfg = read_conf()
            uri = cfg.connection_string

        self.uri = uri
        hub_registry.add(self)
        ConnectionHub.__init__(self)

    def getConnection(self):
        try:
            #print "g1"
            conn = self.threadingLocal.connection
            return conn # different from sqlobject. no transaction needed
        except AttributeError:
            if self.uri:
                conn = connectionForURI(self.uri)
                # the following line effectively turns off the DBAPI connection
                # cache. We're already holding on to a connection per thread,
                # and the cache causes problems with sqlite.
                if self.uri.startswith("sqlite"):
                    TheURIOpener.cachedURIs = {}
                self.threadingLocal.connection = conn
                return conn # self.begin(conn), but no trans needed
            raise AttributeError(
                "No connection has been defined for this thread "
                "or process")

    def reset(self):
        """Used for testing purposes. This drops all of the connections
        that are being held."""
        self.threadingLocal = threading_local()


#This dictionary stores the AutoConnectHubs used for each
# connection URI
_hubs = dict()

class PackageHub(object):
    """Transparently proxies to an AutoConnectHub for the URI
    that is appropriate for this package. A package URI is
    configured via "packagename.dburi" in the global CherryPy
    settings. If there is no package DB URI configured, the
    default (provided by "sqlobject.dburi") is used.

    The hub is not instantiated until an attempt is made to
    use the database.
    """
    # In the current nwu version, packagename is silently ignored
    def __init__(self, packagename=''):
        self.packagename = packagename
        self.hub = None

    def __get__(self, obj, type):
        if not self.hub:
            self.set_hub()
        return self.hub.__get__(obj, type)

    def __set__(self, obj, type):
        if not self.hub:
            self.set_hub()
        return self.hub.__set__(obj, type)

    def __getattr__(self, name):
        if not self.hub:
            self.set_hub()
        return getattr(self.hub, name)

    def set_hub(self):
        global cfg

        if not cfg:
            cfg = read_conf()
        dburi = cfg.connection_string

        if not dburi:
            raise Exception, "No database configuration found."
        hub = _hubs.get(dburi, None)
        if not hub:
            hub = AutoConnectHub(dburi)
            _hubs[dburi] = hub
        self.hub = hub

if __name__ == '__main__':
    bla = PackageHub()
    print bla
