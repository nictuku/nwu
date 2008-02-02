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

Adds support for checking TLS WWW Server and Client OIDs, private key 
generation, X509 CSR generation and signing and some more things not included
in vanilla python-gnutls.
"""

import time

from ctypes import *

from gnutls import crypto
from gnutls.library.constants import *
from gnutls.library.functions import *
from gnutls.library.types import *
from gnutls.validators import method_args, function_args, one_of, ignore
from gnutls.errors import GNUTLSError

__all__ = ['X509Certificate', 'X509PrivateKey', 'X509CRQ']

def algorithm_name(algorithm_type):
    """ Convert algorithm type to human readable string """
    names = { GNUTLS_PK_UNKNOWN: 'unknown',
              GNUTLS_PK_RSA: 'RSA',
              GNUTLS_PK_DSA: 'DSA' }
    try:
        return names[algorithm_type]
    except:
        return names[GNUTLS_PK_UNKNOWN]
    

class X509Certificate(crypto.X509Certificate):
    @method_args(ignore, 
                 one_of(GNUTLS_X509_FMT_PEM, GNUTLS_X509_FMT_DER))
    def __init__(self, input, format=GNUTLS_X509_FMT_PEM):
        if isinstance(input, gnutls_x509_crt_t):
            self._c_object = input
        else:
            crypto.X509Certificate.__init__(self, input, format)
            
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
        size = size_t(1024)
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

    @method_args(one_of(GNUTLS_X509_FMT_PEM, GNUTLS_X509_FMT_DER))
    def export(self, format=GNUTLS_X509_FMT_PEM):
        """ Export X509 certificate """
        size = size_t(40*1024)
        buffer = create_string_buffer(size.value)
        
        gnutls_x509_crt_export(self._c_object, format, 
                               cast(byref(buffer), c_void_p), byref(size))

        return buffer.value

class X509PrivateKey(crypto.X509PrivateKey):
    @method_args(ignore, one_of(GNUTLS_X509_FMT_PEM, GNUTLS_X509_FMT_DER))
    def __init__(self, input, format=GNUTLS_X509_FMT_PEM):
        """ Overrides original __init__ method. 

        Adds support for passing gnutls_x509_privkey_t as first argument.
        """
        if isinstance(input, gnutls_x509_privkey_t):
            self._c_object = input
        else:
            crypto.X509PrivateKey.__init__(self, input, format)

    @staticmethod
    @function_args(int, one_of(GNUTLS_PK_RSA, GNUTLS_PK_DSA))
    def generate(bits=1024, type=GNUTLS_PK_RSA):
        """ Generate a private key. """
        k = gnutls_x509_privkey_t()

        gnutls_x509_privkey_init(k)
        gnutls_x509_privkey_generate(k, type, bits, 0)
        return X509PrivateKey(k)

    def export(self):
        """ Export key in string (X509 PEM format). """
        size = size_t(10*1024)
        buffer = create_string_buffer(size.value)
        gnutls_x509_privkey_export(self._c_object, GNUTLS_X509_FMT_PEM, 
                                   cast(byref(buffer), c_void_p), byref(size))

        return buffer.value

    @property
    def algorithm(self):
        """ Key algorithm type """
        return gnutls_x509_privkey_get_pk_algorithm(self._c_object)
    
    @property
    def algorithm_name(self):
        """ Key algorithm name """
        return algorithm_name(self.algorithm)

    @property
    def key_id(self):
        """ Key ID (as unicode string) """
        size = size_t(128)
        buffer = create_unicode_buffer(size.value)
        res = gnutls_x509_privkey_get_key_id(
            self._c_object, 0, cast(byref(buffer), POINTER(c_ubyte)), 
            byref(size))

        return buffer.value

class X509CRQ(object):
    def __new__(cls, *args, **kwargs):
        instance = object.__new__(cls)
        instance.__deinit = gnutls_x509_crq_deinit
        instance._c_object = gnutls_x509_crq_t()
        return instance

    @method_args(ignore, one_of(GNUTLS_X509_FMT_PEM, GNUTLS_X509_FMT_DER), 
                 ignore)
    def __init__(self, input, format=GNUTLS_X509_FMT_PEM, private_key=None):
        if type(input) == str:
            dat = gnutls_datum_t()

            size = size_t(len(input)+1)
            buffer = create_string_buffer(input)

            dat.size = size
            dat.data = cast(byref(buffer), POINTER(c_ubyte))
            gnutls_x509_crq_init(byref(self._c_object))
            gnutls_x509_crq_import(self._c_object, byref(dat), format)
            
        elif isinstance(input, gnutls_x509_crq_t):
            self._c_object = gnutls_x509_crq_t
            gnutls_x509_crq_sign(self._c_object, private_key)

    @property
    def algorithm(self):
        """ Private key algorithm type """
        return gnutls_x509_crq_get_pk_algorithm(self._c_object, 
                                                byref(c_uint()))

    @property
    def key_length(self):
        """ Private key length """
        length = c_uint()
        gnutls_x509_crq_get_pk_algorithm(self._c_object, byref(length))
        return length.value

    @property
    def algorithm_name(self):
        """ Private key algorithm name """
        return algorithm_name(self.algorithm)

    @property
    def dn(self):
        """ DN """
        size = size_t(1024)
        buf = create_string_buffer(size.value)
        gnutls_x509_crq_get_dn(self._c_object, buf, byref(size))
        return buf.value

    def dn_oids(self):
        """ Get DN OIDs. """
        oids = []
        i = 0
        while True:
            size = c_size_t(128)
            buf = create_string_buffer(size.value)

            try:
                gnutls_x509_crq_get_dn_oid(
                    self._c_object, i, cast(byref(buf), c_void_p), byref(size))
            except GNUTLSError:
                break

            oids.append(buf.value)
            i = i + 1

        return oids

    @method_args(str)
    def get_dn_by_oid(self, oid):
        """ Get value of DN-part by OID (ie. 2.5.4.6 for country value(s)). """
        result = []
        i = 0
        while True:
            size = c_size_t(256)
            buf = create_string_buffer(size.value)
            
            try:
                gnutls_x509_crq_get_dn_by_oid(
                    self._c_object, oid, i, 0, cast(byref(buf), c_void_p),
                    byref(size))
            except:
                break

            result.append(buf.value)
            i = i + 1

        return result
        
        
    def create_certificate(self, ca_privkey, ca_cert, serial_number, 
                           days_valid, **kwargs):
        """ Create a certificate from the CRQ. """
        kp_list = []

        # First thing to do: convert **kwargs to something usable
        for p in kwargs:
            if p == 'tls_www_server':
                kp_list.append(GNUTLS_KP_TLS_WWW_SERVER)
            elif p == 'tls_www_client':
                kp_list.append(GNUTLS_KP_TLS_WWW_CLIENT)
            elif p == 'code_signing':
                kp_list.append(GNUTLS_KP_CODE_SIGNING)
            elif p == 'email_protection':
                kp_list.append(GNUTLS_KP_EMAIL_PROTECTION)
            elif p == 'time_stamping':
                kp_list.append(GNUTLS_KP_TIME_STAMPING)
            elif p == 'ocscp_signing':
                kp_list.append(GNUTLS_KP_OCSP_SIGNING)
            elif p == 'any':
                kp_list.append(GNUTLS_KP_ANY)

        cert = gnutls_x509_crt_t()
        
        res = gnutls_x509_crt_init(byref(cert))

        if res != 0:
            return False

        gnutls_x509_crt_set_crq(cert, self._c_object)

        size = c_size_t(4)
        buffer = create_string_buffer(size.value)

        # Code taken from GnuTLS' src/certtool.c and converted to python.
        buffer[3] = chr(serial_number & 0xff)
        buffer[2] = chr((serial_number >> 8) & 0xff)
        buffer[1] = chr((serial_number >> 16) & 0xff)
        buffer[0] = chr(0)

        gnutls_x509_crt_set_serial(cert, buffer, size)
        gnutls_x509_crt_set_activation_time(cert, int(time.time()))

        # One day = 24 * 3600 seconds
        secs_valid = days_valid * 24 * 3600

        gnutls_x509_crt_set_expiration_time(cert, int(time.time())+secs_valid)
        
        # GnuTLS' certtool always sets the version to 3.
        gnutls_x509_crt_set_version(cert, 3)

        for kp in kp_list:
            gnutls_x509_crt_set_key_purpose_oid(cert, kp, 0)

        size = size_t(1024)
        buffer = create_string_buffer(size.value)

        res = gnutls_x509_crt_get_key_id(cert, 0, 
                                         cast(byref(buffer), POINTER(c_ubyte)),
                                         byref(size))

        if res >= 0:
            gnutls_x509_crt_set_subject_key_id(
                cert, cast(byref(buffer), c_void_p), size)
        
        gnutls_x509_crt_get_key_id(
            ca_cert._c_object, 0, cast(byref(buffer), POINTER(c_ubyte)),
            byref(size))
        gnutls_x509_crt_set_authority_key_id(
            cert, cast(byref(buffer), c_void_p),
            size)            
        
        # XXX: We may want to also support other digest algorithms.
        gnutls_x509_crt_sign2(cert, ca_cert._c_object, ca_privkey._c_object,
                              GNUTLS_DIG_SHA1, 0)

        return X509Certificate(cert)

