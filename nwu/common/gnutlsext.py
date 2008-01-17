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

"""
Python-GnuTLS extensions.

Adds support for checking TLS WWW Server and Client OIDs.
"""

from gnutls import crypto
from gnutls.library.constants import GNUTLS_KP_TLS_WWW_SERVER
from gnutls.library.constants import GNUTLS_KP_TLS_WWW_CLIENT
from gnutls.library.functions import gnutls_x509_crt_get_key_purpose_oid
from gnutls.errors import GNUTLSError
from ctypes import c_size_t, create_string_buffer, c_ulong, byref

class X509Certificate(crypto.X509Certificate):
    @property
    def tls_www_server(self):
        """ Certificate has TLS WWW Server OID. """
        return GNUTLS_KP_TLS_WWW_SERVER in self.get_key_purpose_oids()
    
    @property
    def tls_www_client(self):
        """ Certificate has TLS WWW Client OID. """
        return GNUTLS_KP_TLS_WWW_CLIENT in self.get_key_purpose_oids()

    def get_key_purpose_oids(self):
        """ Get all OIDs from the certificate. """
        size = c_size_t(1024)
        buffer = create_string_buffer(size.value)
        critical = c_ulong()
        i = 0
        oids = []

        while True:
            try:
                gnutls_x509_crt_get_key_purpose_oid(
                    self._c_object, i, byref(buffer), byref(size), 
                    byref(critical))
            except GNUTLSError:
                break

            oids.append(buffer.value)
            i = i + 1

        return oids
