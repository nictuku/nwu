# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Stephan Peijnik
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ChangeLog:
#   2008-01-08  Stephan Peijnik <sp@gnu.org>
#           * Version 0.1
#           * Documentation update.
#           * Added generate_certificate_from_privkey.
#           * Added generate_certificate_from_csr.
#           * Added example code.
#   2008-01-07  Stephan Peijnik <sp@gnu.org>
#           * Initial version.

""" Wrapper for GnuTLS' certtool binary.

This wrapper library gives you access to GnuTLS' certtool which allows one
to create keys, certificates and also sign these.

Example:

# creating a new RSA private key (1024 bits by default)
privKey = generate_privkey()
fp = open('my.key', 'w')
fp.write(privKey)
fp.close()

# creating a certificate authority
ca = create_ca('my.ca.local')
fp = open('ca.crt', 'w')
fp.write(ca['cert'])
fp.close()
fp = open('ca.key', 'w')
fp.write(ca['key'])
fp.close()

# generating a TLS web client CSR
fp = open('my.key', 'r')
key = fp.read()
fp.close()
csr = generate_csr(key, 'AT', 'foo Inc.', 'my.client.foo.inc.local', 
                   ['tls_www_client'])
fp = open('my.csr', 'w')
fp.write(csr)
fp.close()

# creating a certificate from a CSR
fp = open('my.csr', 'r')
csr = fp.read()
fp.close()

fp = open('ca.crt', 'r')
caCert = fp.read()
fp.close()

fp = open('ca.key', 'r')
caKey = fp.read()
fp.close()

crt = generate_certificate_from_csr(caKey, caCert, csr, ['tls_www_client'])

fp = open('my.crt', 'w')
fp.write(crt)
fp.close()

"""

import os
import sys

from tempfile import NamedTemporaryFile

__version__ = '0.1'
__author__ = 'Stephan Peijnik'

# We need to find certtool first and verify its version.
# This needs to be done everytime this module is loaded, so the location
# of this code is alright.

CERTTOOL_BIN=None
CERTTOOL_VERSION=None

# Let's go and find the certtool binary.

CERTTOOL_BIN=os.popen('which certtool').read()

if CERTTOOL_BIN == '':
    print '[ERROR] Calling which certtool failed.'
    print '        Is certtool installed and in your PATH?'
    sys.exit(255)

# remove trailing newline, if present.
CERTTOOL_BIN=CERTTOOL_BIN.strip()

tmp_output=os.popen('%s --version' % (CERTTOOL_BIN)).read()

tmp_info=tmp_output.split(' ', 3)

# tmp_info should now contain: ['certtool', '(GnuTLS)', '<version>'].
# We obviously need to validate that.

if not tmp_info[0].endswith('certtool') or not tmp_info[1].startswith('(GnuTLS'):
    print '[ERROR] certtool seems not to be GnuTLS\' certtool binary.'
    sys.exit(255)

CERTTOOL_VERSION=tmp_info[2]

# Maybe we should do some version checking here.
# This library has been developed using certtool 1.6.3, older and/or newer
# versions may break this library!

def __invoke_ct(command):
    """ Invokes certtool with command as argument(s) """
    return os.popen3('%s %s' % (CERTTOOL_BIN, command))

def __invoke_ct_simple(command):
    """ Invokes certtool but only returns its output (to stdout only!) """
    outfp, infp, errfp = __invoke_ct(command)
    data = infp.read()
    infp.close()
    errfp.close()
    outfp.close()
    return data

def generate_privkey(bits=1024):
    """ Generates a new (RSA) private key, bits is optional and defaults to
    1024 """
    return __invoke_ct_simple('-p --bits %d' % (bits))

def generate_self_signed(privkeyPath, template=[]):
    """ Self-signs a given private key """
    # Template contains all data needed to generate the certificate.
    # Refer to GnuTLS' doc/certtool.cfg for information.
        
    # first we need to write out the template file
    fp = NamedTemporaryFile()
    fileName = fp.name
    for i in template:
        fp.write('%s\n' % (i))
    fp.flush()

    result = __invoke_ct_simple('-s --load-privkey %s --template %s'
                                      % (privkeyPath, fileName))
    fp.close()
    return result
    
def tempFile(data=None):
    """ Creates a new temporary file and fills it with data, if set.
    NOTE: As soon the close() method of the returned file is called it
    is deleted. """
    tmpFile = NamedTemporaryFile()
    if data:
        tmpFile.write(data)
        tmpFile.flush()

    return tmpFile

def create_ca(commonName, bits=1024):
    """ Creates a new CA (certificat authority) using commonName as name
    and optionally bits as length of the private key """
    privKey = generate_privkey(bits)
    privKeyFile = tempFile(privKey)

    privKeyFileName = privKeyFile.name

    template = ['cn = %s' % (commonName), 'ca', 'cert_signing_key']

    cert = generate_self_signed(privKeyFileName, template)
    privKeyFile.close()

    return {'cert': cert, 'key': privKey}

def generate_certificate_from_privkey(caPrivKey, caCert, privKey, template=[]):
    """ creates a certificae from a given private key """
    caPrivKeyFile = tempFile(caPrivKey)
    caCertFile = tempFile(caCert)
    privKeyFile = tempFile(privKey)
    templateFile = tempFile()

    for i in template:
        templateFile.write('%s\n' % (i))
    templateFile.flush()

    result = __invoke_ct_simple('-c --load-ca-privkey %s '
                                '--load-ca-certificate %s '
                                '--load-privkey %s --template %s' 
                                % (caPrivKeyFile.name, caCertFile.name,
                                   privKeyFile.name, templateFile.name))

    caPrivKeyFile.close()
    caCertFile.close()
    privKeyFile.close()
    templateFile.close()
    return result
    
def generate_certificate_from_csr(caPrivKey, caCert, csr, template=[]):
    """ creates a certificate from a given CSR """

    caPrivKeyFile = tempFile(caPrivKey)
    caCertFile = tempFile(caCert)
    csrFile = tempFile(csr)
    templateFile = tempFile()

    for i in template:
        templateFile.write('%s\n' % (i))
    templateFile.flush()

    result = __invoke_ct_simple('-c --load-ca-privkey %s '
                                '--load-ca-certificate %s '
                                '--load-request %s --template %s' % 
                                (caPrivKeyFile.name, csrFile.name,
                                 templateFile.name))

    caPrivKeyFile.close()
    caCertFile.close()
    csrFile.close()
    templateFile.close()

    return result

def generate_csr(privKey, country, orgName, commonName, template=[]):
    """ creates a CSR """
    template += ['cn = %s' % (commonName), 'country = %s' % (country),
                'organization = %s' % (orgName), ]

    privKeyFile = tempFile(privKey)

    templateFile = tempFile()
    for i in template:
        templateFile.write('%s\n' % (i))
    templateFile.flush()

    result = __invoke_ct_simple('-q --load-privkey %s --template %s'
                             % (privKeyFile.name, templateFile.name))
    templateFile.flush()
    privKeyFile.flush()

    return result
