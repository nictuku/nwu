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

from ctypes import *

from gnutls import crypto
from gnutls.library.constants import *
from gnutls.library.functions import *
from gnutls.library.types import *
from gnutls.validators import method_args, function_args, one_of
from gnutls.errors import GNUTLSError

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

class X509PrivateKey(crypto.X509PrivateKey):
    @staticmethod
    @function_args(int, one_of(GNUTLS_PK_RSA, GNUTLS_PK_DSA))
    def generate(bits=1024, type=GNUTLS_PK_RSA):
        """ Generate a private key. """
        k = gnutls_x509_privkey_t()

        gnutls_x509_privkey_init(k)
        gnutls_x509_privkey_generate(k, type, bits, 0)

        # XXX: Evil workaround.
        size = c_size_t(10*1024)
        buffer = create_string_buffer(size.value)
        gnutls_x509_privkey_export(k, GNUTLS_X509_FMT_PEM, 
                                   cast(byref(buffer), c_void_p), byref(size))
        return X509PrivateKey(buffer.value)

    def export(self):
        size = c_size_t(10*1024)
        buffer = create_string_buffer(size.value)
        gnutls_x509_privkey_export(self._c_object, GNUTLS_X509_FMT_PEM, 
                                   cast(byref(buffer), c_void_p), byref(size))

        return buffer.value
