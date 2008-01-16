# SecureXMLRPC.py - gnutls-enabled XML-RPC Server and Client
#
# Copyright (C) 2007, 2008 Stephan Peijnik
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesse General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ChangeLog:
#   2008-01-13   Stephan Peijnik <sp@gnu.org>
#          * SecureXMLRPCServer is now multithreaded.
#          * Version 0.3.4
#  
#   2008-01-09   Stephan Peijnik <sp@gnu.org>
#          * Support for gzip compressed XML-RPC.
#          * ChangeLog cleanup (we needed a few spaces for this to look
#            good).
#          * Version 0.3.3
#
#   2008-01-08   Stephan Peijnik <sp@gnu.org>
#           * Pass X509 certificate information down to called method.
#           * Fixing problems with stale connection (only caused by old 
#             clients).
#           * Finally fix unclean socket shutdown in server.
#           * Documentation of the client code.
#           * Preparations for TLS authentication support.
#             NOTE: For this to work both the client and the server need
#                   a valid certificate signed by the same CA!
#           * Version 0.3.2
#
#   2008-01-05  Stephan Peijnik <sp@gnu.org>
#           * Changed versioning scheme to x.y.z instead of x.y
#           * Version 0.3.1
#           * Fix problems with 'anonymous' clients.
#           * Fix unclean socket shutdown in server (breaks GnuTLS client!).
#
#   2008-01-04  Stephan Peijnik <sp@gnu.org>
#           * Version 0.3
#           * Added SecureProxy and SecureTransport (client) classes.
#
#   2008-01-03  Stephan Peijnik <sp@gnu.org>
#           * Version 0.2
#           * Now using PEM file instead of separate key/cert files.
#           * Updated documentation to reflect changes.
#
#   2007-10-07  Stephan Peijnik <sp@gnu.org>
#           * Version 0.1, initial release.

"""A gnutls-enabled XML-RPC Server and Client.

This module extends the SimpleXMLRPCServer and xmllib/httplib modules as 
shipped with Python and adds support for encrypted (https, TLS) connections.

The SecureXMLRPCServer works the same way SimpleXMLRPCServer.SimpleXMLServer
does, except for instance creation, which requires one additional argument,
the path to a PEM file (containing a certificate and a private key).

Also, every method is supplied with an additional argument (as first argument),
being the client's X509 certificate.
ie. If the client calls foo(1, 5) this will become foo(X509Info, 1, 5).

These files can be created using gnutls' certtool. For more information see
http://www.gnu.org/software/gnutls/manual/html_node/Invoking-certtool.html.

The SecureTransport and SecureProxy implement the gnutls-enabled client.
SecureProxy works the same way xmllib.ServerProxy does and SecureTransport
provides the gnutls-enabled transport to use.

Starting at version 0.3.3 SecureProxy and SecureXMLRPCServer support gzip
compression of the XML payload. This works transparently and has only one
consequence: The client tries to compress its first request, if that
yields an error compression is turned off and the request re-sent. However,
if the re-sent request also fails compression is turned on again.


Compressed vs. uncompressed XMLRPC:

A test was done by calling an unexistant help() method and thus receiving
a fault. The results can be found below.

Uncompressed:

Request :  98 Bytes
Response: 321 Bytes

Compressed:

Request :  82 Bytes
Response: 192 Bytes  


License: LGPLv3 or later, see module sourcecode for more information.
"""

import os.path
import socket
import sys
import xmlrpclib

from httplib import HTTP, HTTPConnection, HTTPS_PORT, FakeSocket
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, Fault
from SocketServer import ThreadingTCPServer
from socket import _fileobject

try:
    import fcntl
except ImportError:
    fcntl = None

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
__version__ = '0.3.4'

try:
    import gzip
    HAVE_gzip = True
except:
    HAVE_gzip = False

try:
    import cStringIO
    HAVE_cStringIO = True
except:
    HAVE_cStringIO = False

if HAVE_gzip and HAVE_cStringIO:
    HAVE_COMPRESSION = True
    def gzip_buffer(buffer, compresslevel=6):
        """ Compress buffer with gzip and return it. """
        gzipped = cStringIO.StringIO()
        gzipFile = gzip.GzipFile(mode='wb', compresslevel=compresslevel, 
                                 fileobj=gzipped)
        gzipFile.write(buffer)
        gzipFile.close()
        return gzipped.getvalue()

    def degzip_buffer(gz_buffer):
        """ Decompress gzipped data and return it. """
        gzipped = cStringIO.StringIO()
        gzipped.write(gz_buffer)
        gzipped.flush()
        gzipped.seek(0)
        gzipFile = gzip.GzipFile(mode='rb', fileobj=gzipped)
        return gzipFile.read()
else:
    HAVE_COMPRESSION = False

class SecureServerConnection(ServerSession):
    """ Extends GnuTLS' ServerSession """
    def shutdown(self, *args):
        """ Overrides GnuTLS' ServerSession.shutdown.
        
        Needed in order to avoid problems in the client. """

        # Seems like this is the final fix to the problem:
        # GnuTLS uses TLS 1.1, whilst OpenSSL seems to use TLS 1.0.
        # The GnuTLS clients require the server to do a graceful shutdown,
        # whilst the OpenSSL clients break if you do a graceful shutdown
        # of the connection.
        # NOTE: This could be a workaround and might need some additional 
        #       testing!
        #       This needs some research, it's likely that this is a bug in
        #       OpenSSL or python's SSL implementation.
        if self.protocol == 'TLS 1.1':
            try:
                self.bye()
            except Exception, e:
                pass
        self.socket.shutdown(0)

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
        self.certificate = self.request.peer_certificate

    def do_POST(self):
        """Overrides SimpleXMLRPCRequestHandler's do_POST method.

        This method is heavily based on the code found in the original do_POST
        method of SimpleXMLRPC's SimpleXMLRPCServer.
        However, there was a need to re-implement the method to pass
        an additional argument, the client certificate, down to the
        server's _marshaled_dispatch method.

        The original code was written by Brian Quinlan (brian@sweetapp.com)
        and was based on code written by Fredrik Lundh.
        """
        gzip_response = False

        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        try:
            # Get arguments by reading body of request.
            # We read this in chunks to avoid straining
            # socket.read(); around the 10 or 15Mb mark, some platforms
            # begin to have problems (buf #792570).
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)

            # Check for gzipped body.
            if self.headers.has_key('Content-Encoding') and \
                    self.headers['Content-Encoding'] == 'gzip':
                if not HAVE_COMPRESSION:
                    # Simply raising an exception will cause a 500 response
                    raise

                # decompress
                data = degzip_buffer(data)
            
            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overriden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using the method if present (Should not apply for us).
            #
            # Two additional arguments (certificate, remote_host) are passed 
            # to the dispatcher method.
            remote_host = self.request.socket.getpeername()[0]

            response = self.server._marshaled_dispatch(
                data, getattr(self, '_dispatch', None), self.certificate,
                remote_host)
        except Exception, e:
            # interal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            
            # Check if the client supports gzip
            if self.headers.has_key('Accept-Encoding') and \
                    'gzip' in self.headers['Accept-Encoding'] and \
                    HAVE_COMPRESSION:
                self.send_header('Content-Encoding', 'gzip')
                response = gzip_buffer(response)

            self.send_header("Content-length", str(len(response)))
            self.end_headers()

            self.wfile.write(response)
            self.wfile.flush()
            self.connection.shutdown(1)

class SecureXMLRPCServer(SimpleXMLRPCDispatcher, ThreadingTCPServer):
    """Implements a gnutls-enabled XML-RPC server"""

    allow_reuse_address = True

    def __init__(self, addr, key_file, cert_file, ca_cert_file, 
                 allow_none=False, encoding=None, *args, 
                 **kwargs):
        """Initialize a new instance, passing the bind address and
        the path to a PEM file."""
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file
        self.logRequests = False

        self._tls_init()

        if kwargs.has_key('requestHandler'):
            del kwargs['requestHandler']

        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)
        ThreadingTCPServer.__init__(self, addr, SecureRequestHandler)

        # Just like in SimpleXMLRPCServer we need to set the close-on-exec 
        # flag
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

    def _tls_init(self):
        """Initialize gnutls.
        
        Creates an X509Credentials instance using the PEM file pased to 
        __init__.
        """
        if not os.path.exists(self.key_file) or \
                not os.path.exists(self.cert_file):
            print '[ERROR] Key or certificate file missing.'
            sys.exit(255)

        cert = X509Certificate(open(self.cert_file).read())
        key = X509PrivateKey(open(self.key_file).read())
        ca_cert = X509Certificate(open(self.ca_cert_file).read())
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
            try:
                if session.protocol == 'TLS 1.1':
                    session.bye()
            except Exception, e:
                # ignore any exceptions here!
                pass
            new_sock.close()
            # raising a socket error should cause SocketServer.BaseServer's
            # handle_request to return cleanly.
            # WARNING: This is going to cause a ProtocolError in the client!
            raise socket.error()

        return (session, addr)

    def _marshaled_dispatch(self, data, dispatch_method = None, 
                            certificate=None, remote_host=None):
        """ Overrides SecureXMLRPCDispatcher's _marshaled_dispatch method.

        This method is heavily based on the code found in the original 
        _marshaled_dispatch method of SimpleXMLRPC's SimpleXMLRPCDispatcher.   

        However, there was a need to re-implement the method to pass           
        an additional argument, the client certificate, down to the            
        server's _dispatch method.                                   
                                                                               
        The original code was written by Brian Quinlan (brian@sweetapp.com)    
        and was based on code written by Fredrik Lundh.   
        """
        
        try:
            params, method = xmlrpclib.loads(data)

            # inject certificate and remote_host as first two values
            # into params.
            # XXX: Is there a cleaner way to do this?
            params_new = (certificate, remote_host, )
            params_new += params
            params = params_new

            # generate response
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpclib.dumps(response, methodresponse=1,
                                       allow_none=self.allow_none, 
                                       encoding=self.encoding)
        except Fault, fault:
            response = xmlrpclib.dumps(fault, allow_none=self.allow_none,
                                       encoding=self.encoding)
        except:
            # report exception back to server
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value)),
                encoding=self.encoding, allow_none=self.allow_none,
                )

        return response
        

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
        # Client side workaround of the GnuTLS vs. OpenSSL issue.
        # This should the client cause not to break even after an unclean
        # shutdown of the connection.
        try:
            return self.recv(size)
        except Exception, e:
            return ''

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

class SecureTransport(xmlrpclib.Transport):
    """ GnuTLS-enabled Transport for httplib. """
    user_agent = "SecureXMLRPC/%s" % (__version__)

    class GzipParser:
        def __init__(self, parser):
            self.gz_buffer = ''
            self.parser = parser

        def feed(self, data):
            self.gz_buffer += data

        def close(self):
            buffer = degzip_buffer(self.gz_buffer)
            self.parser.feed(buffer)
            self.parser.close()

    def __init__(self, credentials, use_datetime=0, anonymous=False):
        """ Initializes SecureTransport. """
        self.credentials = credentials
        self.anonymous = anonymous
        self.disable_gzip = False

        xmlrpclib.Transport.__init__(self, use_datetime)

    def request(self, host, handler, request_body, verbose=0):
        """ Implements fallback to non-gzip mode in case of an error in
        gzip mode. 

        If the error was a real one it's going to be reported back.
        """
        if not self.disable_gzip and HAVE_COMPRESSION:
            try:
                res = xmlrpclib.Transport.request(self, host, handler, 
                                                  request_body,
                                                  verbose=verbose)
                return res
            except xmlrpclib.ProtocolError:
                # Fall back to non-gzip mode, re-send request.
                self.disable_gzip = True
                return self.request(host, handler, request_body, 
                                    verbose=verbose)

        try:
            result = xmlrpclib.Transport.request(self, host, handler, 
                                                 request_body, verbose=verbose)
        except xmlrpclib.ProtocolError:
            # Another error in non-gzip mode? Enable compression again!
            if HAVE_COMPRESSION:
                self.disable_gzip = False
            raise

        return result

    def getparser(self):
        """ Overrides xmlrpclib.Transport.getparser().

        This method injects the GzipParser if gzip is enabled.
        """
        parser, unmarshaller = xmlrpclib.Transport.getparser(self)
        if not self.disable_gzip and HAVE_COMPRESSION:
            parser = self.GzipParser(parser)
        return parser, unmarshaller

    def send_content(self, connection, request_body):
        """ Sends the content and gzip-compresses it if possible """
        # Always tell the server we accept gzipped responses.
        if HAVE_COMPRESSION:
            connection.putheader('Accept-Encoding', 'gzip')

        if not self.disable_gzip and HAVE_COMPRESSION:
            connection.putheader('Content-Encoding', 'gzip')
            request_body = gzip_buffer(request_body)

        return xmlrpclib.Transport.send_content(self, connection, request_body)

    def make_connection(self, host):
        """ Creates a new (TLS) connection to the given host. """
        host, extra_headers, ignore = self.get_host_info(host)
        return GNUTLSHTTPS(host, None, self.credentials, 
                           anonymous=self.anonymous)

class SecureProxy(xmlrpclib.ServerProxy):
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
        xmlrpclib.ServerProxy.__init__(self, uri, t, encoding, verbose, 
                                       allow_none, use_datetime)
