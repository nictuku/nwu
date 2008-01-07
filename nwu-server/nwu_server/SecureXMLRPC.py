# SecureXMLRPC.py - gnutls-enabled XML-RPC Server and Client
#
# Copyright (C) 2007, 2008 Stephan Peijnik
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesse General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ChangeLog:
#   2008-01-08   Stephan Peijnik <sp@gnu.org>
#           * Documentation of the client code.
#           * Preparations for TLS authentication support.
#             NOTE: For this to work both the client and the server need
#                   a valid certificate signed by the same CA!
#   2008-01-05  Stephan Peijnik <sp@gnu.org>
#           * Changed versioning scheme to x.y.z instead of x.y
#           * Version 0.3.1
#           * Fix problems with 'anonymous' clients.
#           * Fix unclean socket shutdown in server (breaks GnuTLS client!).
#   2008-01-04  Stephan Peijnik <sp@gnu.org>
#           * Version 0.3
#           * Added SecureProxy and SecureTransport (client) classes.
#   2008-01-03  Stephan Peijnik <sp@gnu.org>
#           * Version 0.2
#           * Now using PEM file instead of separate key/cert files.
#           * Updated documentation to reflect changes.
#
#   2007-10-07  Stephan Peijnik <sp@gnu.org>
#           * Version 0.1, initial release.
#
#
# TODO:
#  * Inject session.peer_certificate into *EVERY* XML-RPC request
#    (ie. call to foo(5, 3) becomes foo(session.peer_certificate, 5, 3) or
#    find another way to do proper authentication.

"""A gnutls-enabled XML-RPC Server and Client.

This module extends the SimpleXMLRPCServer and xmllib/httplib modules as 
shipped with Python and adds support for encrypted (https, TLS) connections.

The SecureXMLRPCServer works the same way SimpleXMLRPCServer.SimpleXMLServer
does, except for instance creation, which requires one additional argument,
the path to a PEM file (containing a certificate and a private key).

These files can be created using gnutls' certtool. For more information see
http://www.gnu.org/software/gnutls/manual/html_node/Invoking-certtool.html.

The SecureTransport and SecureProxy implement the gnutls-enabled client.
SecureProxy works the same way xmllib.ServerProxy does and SecureTransport
provides the gnutls-enabled transport to use.

License: LGPLv3 or later, see module sourcecode for more information.
"""

import os.path
import socket
import sys

from httplib import HTTP, HTTPConnection, HTTPS_PORT, FakeSocket
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from socket import _fileobject
from xmlrpclib import Transport, ServerProxy

try:
    import gnutls
    from gnutls.library.errors import CertificateSecurityError
except ImportError, e:
    print '[ERROR] python-gnutls could not be imported.'
    print '        Please install python-gnutls.'
    sys.exit(255)

from gnutls.connection import X509Credentials, X509Certificate, \
    X509PrivateKey, ServerSession, ClientSession
from gnutls.errors import CertificateSecurityError


__all__ = ['SecureXMLRPCServer', 'SecureRequestHandler', 'SecureProxy',
           'SecureTransport']
__version__ = '0.3.1'

class SecureServerConnection(ServerSession):
    """ Extends GnuTLS' ServerSession """
    def shutdown(self, *args):
        """ Overrides GnuTLS' ServerSession.shutdown.
        
        Needed in order to avoid problems in the client. """
        # NOTE: simply closing the connection will cause the client,
        #       even though it may have received a valid reply from the server
        #       to report an invalid TLS packet length (only GnuTLS seems to be
        #       affected by this).
        self.bye()

class SecureRequestHandler(SimpleXMLRPCRequestHandler):
    """Extends SimpleXMLRPCRequestHandler."""
    def setup(self):
        """Overrides SocketServer.StreamRequestHandler's setup method.

        Replaces SocketServer.StreamRequestHandler's rfile and wfile
        attributes with gnutls-aware ones. This provides transparent
        en-/decryption.
        """
        SimpleXMLRPCRequestHandler.setup(self)
        self.rfile = _fileobject(self.request, 'rb', self.rbufsize)
        self.wfile = _fileobject(self.request, 'wb', self.wbufsize)
        # XXX: debug, print certificate
        #      any other value than None means the client presented us with
        #      a valid certificate.
        print 'client cert: %s' % (session.peer_certificate)

class SecureXMLRPCServer(SimpleXMLRPCServer):
    """Implements a gnutls-enabled XML-RPC server"""
    def __init__(self, addr, pem_file, ca_cert_file, *args, **kwargs):
        """Initialize a new instance, passing the bind address and
        the path to a PEM file."""
        self.__addr = addr
        self.__pem_file = pem_file
        self.__ca_cert_file = ca_cert_file

        self.__tls_init()

        if kwargs.has_key('requestHandler'):
            del kwargs['requestHandler']

        SimpleXMLRPCServer.__init__(self, addr, 
                                    requestHandler=SecureRequestHandler,
                                    *args, **kwargs)

    def __tls_init(self):
        """Initialize gnutls.
        
        Creates an X509Credentials instance using the PEM file pased to 
        __init__.
        """
        if not os.path.exists(self.__pem_file):
            print '[ERROR] TLS PEM file does not exist: %s' % (self.__pem_file)
            sys.exit(255)
        cert = X509Certificate(open(self.__pem_file).read())
        key = X509PrivateKey(open(self.__pem_file).read())
        ca_cert = X509Certificate(open(self.__ca_cert_file).read())
        self.__X509Creds = X509Credentials(cert, key, [ca_cert])

    def get_request(self):
        """Handle an incoming connection.
        
        Overrides SecureXMLRPCServer.get_request and provides
        transparent encryption this way.

        WARNING: This method automatically drops connections for which
        the TLS handshake fails!
        """
        new_sock, addr = self.socket.accept()
        session = SecureServerConnection(new_sock, self.__X509Creds)
        try:
            session.handshake()
            peer_cert = session.peer_certificate
            try:
                peer_name = peer_cert.subject
            except AttributeError, e:
                peer_name = 'Unknown'

            # If verify_peer fails the client might be an anonymous one.
            # We still want these to be able to connect in order to ie. 
            # retrieve the CA certificate, send CRLs and retrieve their
            # certificates (needs to be discussed).
            try:
                session.verify_peer()
            except CertificateSecurityError, e:
                pass
        except Exception, e:
            print 'Handshake failed: %s' % (e)
            session.bye()
            new_sock.close()
            # raising a socket error should cause SocketServer.BaseServer's
            # handle_request to return cleanly.
            # WARNING: This is going to cause a ProtocolError in the client!
            raise socket.error()

        return (session, addr)

###
### Client implementation
###

class GNUTLSSocket(ClientSession):
    """ Overrides GnuTLS' ClientSession 

    This class makes ClientSession behave more like OpenSSL's
    SSL socket class and makes it compatible with the xmlrpclib.ServerProxy
    implementation."""
    def __init__(self, sock, creds):
        """ Initializes a new GNUTLSSocket """
        ClientSession.__init__(self, sock, creds)

    def makefile(self, mode, bufsize=None):
        """ Creates a new file object from the GnuTLS socket. """
        return _fileobject(self, mode, bufsize)

    def write(self, buffer):
        """ Writes data to the socket (ClientSession does not implement write
        but send)."""
        return self.send(buffer)

    def read(self, size):
        """ Reads data from the socket (ClientSession does not implement read
        but recv)."""
        return self.recv(size)

class GNUTLSHTTPSConnection(HTTPConnection):
    """ This class implements communication via GNUTLS (SSL/TLS) """

    default_port = HTTPS_PORT

    def __init__(self, host, port=None, credentials=None, strict=None,
                 anonymous=False):
        """ Initializes a new GnuTLS-enabled HTTPS connection. """
        HTTPConnection.__init__(self, host, port, strict)
        
        self.credentials = credentials
        self.anonymous = anonymous
        self.sock = None

    def connect(self):
        """ Connect to a host on a given (SSL) port. """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))

        session = GNUTLSSocket(sock, self.credentials)

        try:
            session.handshake()
            server_cert = session.peer_certificate

            try:
                peer_name = session.peer_certificate
            except AttributeError, e:
                peer_name = 'Unknown'

            if not self.anonymous:
                session.verify_peer()
            # for anonymous clients it does not make sense to verify the peer's
            # certificate (we don't have the CA file yet).

        except Exception, e:
            print 'Handshake failed: %s' % (e)
            session.bye()
            sock.close()
            raise

        self.sock = FakeSocket(sock, session)

class GNUTLSHTTPS(HTTP):
    """ Overrides httplib.HTTP to provide a GnuTLS-enabled
    HTTPS  implementation. """
    _connection_class = GNUTLSHTTPSConnection

    def __init__(self, host='', port=None, credentials=None,
                 strict=0, anonymous=False):
        """ Initializes new HTTPS connection, adds anonymous
        argument. """
        if port == 0:
            port = None

        self._setup(self._connection_class(host, port, credentials, strict, 
                                           anonymous=anonymous))

class SecureTransport(Transport):
    """ GnuTLS-enabled Transport for httplib. """
    user_agent = "SecureXMLRPC/%s" % (__version__)

    def __init__(self, credentials, use_datetime=0, anonymous=False):
        """ Initializes SecureTransport. """
        self.credentials = credentials
        self.anonymous = anonymous
        Transport.__init__(self, use_datetime)

    def make_connection(self, host):
        """ Creates a new (TLS) connection to the given host. """
        host, extra_headers, ignore = self.get_host_info(host)
        return GNUTLSHTTPS(host, None, self.credentials, 
                           anonymous=self.anonymous)

class SecureProxy(ServerProxy):
    """ Overrides xmlrpclib.ServerProxy. """
    def __init__(self, uri, pem_file=None, key_file=None, cert_file=None,
                 ca_cert_file=None, encoding=None, 
                 verbose=0, allow_none=0, use_datetime=0):
        """ Initializes a new proxy class using GnuTLS for encryption. 

        Overrides xmlrpclib.ServerProxy.__init__

        Added arguments:

        pem_file     - PEM file containing both a certificate and private key.
        key_file     - File containing private key.
        cert_file    - File containing client certificate.
        ca_cert_file - File containing CA certificate.

        If none of these files is provided the client will enter 'anonymous'
        mode.
        If either pem_file and ca_cert_file or all three of key_file, cert_file
        and ca_cert_file are provided TLS authentication will be possible.

        NOTE: The server needs a certifiate signed by the CA for which
              the ca_cert_file is provided.
        """
        self.anonymous = False
        self.pem_file = pem_file
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file
        ca = None

        if self.ca_cert_file:
            if not os.path.exists(self.ca_cert_file):
                raise Exception('TLS CA certificate file does not exist: %s'
                                % (self._ca_cert_file))

            fp = open(self.ca_cert_file)
            ca_contents = fp.read()
            ca = X509Certificate(ca_contents)
            fp.close()

        # first try using the PEM file and then fall back to key/cert files    
        if self.pem_file:
            if not os.path.exists(self.pem_file):
                raise Exception('TLS PEM file does not exist: %s' %
                                (self.pem_file))
            fp = open(self.pem_file)
            pemcontents = fp.read()
            fp.close()

            cert = X509Certificate(pemcontents)
            key = X509PrivateKey(pemcontents)
            self.credentials = X509Credentials(cert, key, [ca])

        elif self.key_file and cert_file:
            if not os.path.exists(self.key_file):
                raise Exception('TLS key file does not exist: %s' %
                                (self.key_file))
            if not os.path.exists(self.cert_file):
                raise Exception('TLS cert file does not exist: %s' %
                                (self.cert_file))
            
            fp = open(self.key_file)
            keycontents = fp.read()
            fp.close()

            fp = open(self.cert_file)
            certcontents = fp.read()
            fp.close()

            cert = X509Certificate(certcontents)
            key = X509PrivateKey(keycontents)

            self.credentials = X509Credentials(cert, key, [ca])

        else:
            # anonymous connection
            self.credentials = X509Credentials(None, None)
            self.anonymous = True


        t = SecureTransport(credentials=self.credentials, 
                            use_datetime=use_datetime, 
                            anonymous=self.anonymous)
        ServerProxy.__init__(self, uri, t, encoding, verbose, allow_none, 
                             use_datetime)
