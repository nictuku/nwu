#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006, 2007, 2008 Yves Junqueira (yves@cetico.org) 
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

import logging
import logging.handlers
import os
import pwd
import stat
import sys
import traceback

# for socket.error
import socket

from gnutls.crypto import X509Certificate, X509PrivateKey

from nwu.common import certtool
from nwu.common.app import Application, Command
from nwu.common.SecureXMLRPC import SecureXMLRPCServer

from nwu.server.db.model import db_bind, create_tables
from nwu.server.rpc import RPCDispatcher, PRIV_ANONYMOUS, PRIV_ADMIN
from nwu.server.rpc import PRIV_AGENT 
from nwu.server.rpc.anonymous import AnonymousHandler
from nwu.server.rpc.admin import AdminHandler
from nwu.server.rpc.agent import AgentHandler

class ServerRootCommand(Command):
    def execute(self, app, args, cmd_name=None):
        if len(args) > 0 or cmd_name:
            if cmd_name:
                arg = cmd_name
            else:
                arg = args[0]
                
            self.show_help(app, message='Unknown option: %s' % (arg))
            app.exit(255)

        app.error_log_path = self.option_get_value('errorlog')
        app.pid_file_path = self.option_get_value('pidfile')
        app.config_file_path = self.option_get_value('configfile')

        # First thing to do is initializing logging.
        app.init_logging(not self.option_is_set('foreground'))

        # At this point we can load the server's configuration file.
        app.read_config()

        if self.option_is_set('initialize'):
            app.initialize(self.option_is_set('force-init'))

        if not self.option_is_set('foreground'):
            app.log.info('Daemonizing.')
            app.daemonize()
        app.drop_privileges()

        app.init_crypto()
        app.init_db()

        # This method should never return as it starts the server.
        app.init_server()

class CryptoHelper:
    # As discussed on the mailing list: 730 days is probably a good choice
    # for certificates to expire.
    CERT_EXPIRATION_DAYS = 730

    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.log = app.log
        self.admin_key = app.config_path(app.config.get(\
                'crypto', 'adminkey', app.DEFAULT_ADMIN_KEY))
        self.admin_cert = app.config_path(app.config.get(\
                'crypto', 'admincert', app.DEFAULT_ADMIN_CERT))

    def init_crypto(self):
        self.log.debug("INIT: crypto")
        # step 0: reset/create ca_serial file
        try:
            os.chmod(self.app.ca_serial, stat.S_IWUSR)
        except OSError:
            # File not found
            pass

        try:
            fp = open(self.app.ca_serial, 'w')
        except IOError, e:
             message = 'Could not write to %s: %s' % (self.app.ca_serial, 
                e.strerror)
             self.log.fatal(message)
             sys.exit(1)

        fp.write('1')
        fp.close()
        # IMPORTANT: Fix file permissions on ca_serial file.
        os.chmod(self.app.ca_serial, stat.S_IRUSR)

        self.log.info('CA serial file re-set.')

        if os.path.exists(self.app.ca_key):
            os.chmod(self.app.ca_key, stat.S_IRUSR|stat.S_IWUSR)
        if os.path.exists(self.app.server_key):
            os.chmod(self.app.server_key, stat.S_IRUSR|stat.S_IWUSR)

        # step 1: create CA key/serial
        ca_name = self.get_input('Please enter the CA\'s name: ',
                                 'CA name')

        self.log.info('Generating CA private key and certificate. This may '
                      'take some time.')
        ca = certtool.create_ca(ca_name)
        self.log.info('CA private key and certificate created.')
        fp = open(self.app.ca_cert, 'w')
        fp.write(ca['cert'])
        fp.close()
        fp = open(self.app.ca_key, 'w')
        fp.write(ca['key'])
        fp.close()

        # IMPORTANT: Fix file permissions on CA key file.
        os.chmod(self.app.ca_key, stat.S_IRUSR)

        self.log.info('Generating server private key. This may take some '
                      'time.')
        server_key = certtool.generate_privkey()
        self.log.info('Server private key created.')

        fp = open(self.app.server_key, 'w')
        fp.write(server_key)
        fp.close()

        # IMPORTANT: Fix file permissions on server key file.
        os.chmod(self.app.server_key, stat.S_IRUSR)

        server_name = self.get_input('Please enter the server name: ',
                                     'server name')
        server_org = self.get_input('Please enter your organization: ',
                                    'organization')
        template = ['cn = %s' % (server_name), 
                    'organization = %s' % (server_org),
                    'tls_www_server', 'encryption_key', 'signing_key',
                    'serial = %s' % (self.get_next_serial()),
                    'expiration_days = %d' 
                    % (CryptoHelper.CERT_EXPIRATION_DAYS)]
        server_cert = certtool.generate_certificate_from_privkey(
            ca['key'], ca['cert'], server_key, template)

        self.log.info('Server certificate created.')
        fp = open(self.app.server_cert, 'w')
        fp.write(server_cert)
        fp.close()

        self.log.info('Generating administrator client private key. This'
                      ' may take some time.')

        admin_key = certtool.generate_privkey()
        self.log.info('Administrator client key generated.')
        fp = open(self.admin_key, 'w')
        fp.write(admin_key)
        fp.close()
        os.chmod(self.admin_key, stat.S_IRUSR)

        self.log.info('Generating administrator client certificate.')

        admin_serial = self.get_next_serial()
        template = ['cn = root', 'tls_www_client', 
                    'serial = %s' % (admin_serial),
                    'expiration_days = %s' \
                        % (CryptoHelper.CERT_EXPIRATION_DAYS)]
        admin_cert = certtool.generate_certificate_from_privkey(
            ca['key'], ca['cert'], admin_key, template)

        fp = open(self.admin_cert, 'w')
        fp.write(admin_cert)
        fp.close()
        self.log.info('Administrator client certificate generated.')

        self.log.info('Crypto initialization finished.')

    def get_input(self, request, target):
        while True:
            inp = raw_input(request)
            print 'Is the ' + target + ' "%s" correct?' % (inp)
            res = raw_input('(yes/no) ')
            if res.lower() == 'yes':
                return inp

    def get_next_serial(self):
        fp = open(self.app.ca_serial, 'r')
        cur_serial = int(fp.read())
        fp.close()
        os.chmod(self.app.ca_serial, stat.S_IWUSR|stat.S_IRUSR)
        fp = open(self.app.ca_serial, 'w')
        fp.write(str(cur_serial + 1))
        fp.close()
        os.chmod(self.app.ca_serial, stat.S_IRUSR)
        return cur_serial

    def sign_csr(self, csr):
        ca_cert = open(self.app.ca_cert, 'r').read()
        ca_key = open(self.app.ca_key, 'r').read()
        serial = self.get_next_serial()
        cert = certtool.generate_certificate_from_csr(
            ca_key, ca_cert, csr, ['tls_www_client', 'serial = %d' 
                                   % (serial),
                                   'expiration_days = %d' 
                                   % (CryptoHelper.CERTIFICATE_EXPIRATION_DAYS)
                                   ])
        return {'certificate': cert, 'serial': serial}
                                                      
        

class Server(SecureXMLRPCServer):
    def __init__(self, host, port, app):
        SecureXMLRPCServer.__init__(self, (host, port),
                                    app.server_key, app.server_cert,
                                    app.ca_cert)

        self.dispatcher = RPCDispatcher(app)
        self.register_instance(self.dispatcher)
        # Register handler classes.
        self.dispatcher.register_handler('anon', AnonymousHandler(app), 
                                         PRIV_ANONYMOUS)
        self.dispatcher.register_handler('admin', AdminHandler(app),
                                         PRIV_ADMIN)
        self.dispatcher.register_handler('agent', AgentHandler(app),
                                         PRIV_AGENT)

class ServerApp(Application):
    # DEFAULT SETTINGS
    DEFAULT_DB_DB = '/var/lib/nwu/nwu.db'
    DEFAULT_DB_TYPE = 'sqlite'
    DEFAULT_CONFIG_BASE = '/etc/nwu/'
    DEFAULT_CONFIG = '/etc/nwu/server.conf'
    DEFAULT_CA_CERT = 'cacert.pem'
    DEFAULT_CA_KEY = 'cakey.pem'
    DEFAULT_SERVER_CERT = 'server.crt'
    DEFAULT_SERVER_KEY = 'server.key'
    DEFAULT_CA_SERIAL = 'ca_serial'
    DEFAULT_CA_CRL = 'ca.crl'
    DEFAULT_ADMIN_CERT = 'admin.crt'
    DEFAULT_ADMIN_KEY = 'admin.key'
    DEFAULT_ERRORLOG = '/dev/null'
    DEFAULT_LOGLEVEL = 'INFO'
    DEFAULT_PIDFILE = '/var/run/nwu/nwu-server.pid'
    DEFAULT_USER = 'nwuserver'
    DEFAULT_SERVER_HOST = 'localhost'
    DEFAULT_SERVER_PORT = 8088

    def __init__(self, args=sys.argv[1:], bin_name=sys.argv[0]):
        Application.__init__(self, args, bin_name, 
                             root_command_class=ServerRootCommand)

        self.log = logging.getLogger()

        self.pid_file_path = None
        self.error_log_path = None

        optreg = self.root_command.register_option

        optreg('configfile', 'Specify the config file to read options from.',
               'c', argument=True, default=ServerApp.DEFAULT_CONFIG)
        optreg('errorlog', 'Set file to send untreated python errors to', 'e',
               argument=True, default=ServerApp.DEFAULT_ERRORLOG)
        optreg('force-init', 'Force database initialization even if DB type '
               'is not SQLite.')
        optreg('foreground', 'Do not fork to background.', 'f')
        optreg('initialize', 'Initialize the server environment (database) '
               ' and exit.', 'i')
        optreg('loglevel', 'Set verbosity.', 'l', argument=True,
               default=ServerApp.DEFAULT_LOGLEVEL,
               valid_values=['DEBUG', 'INFO', 'WARNING', 'WARN','ERROR', 
               'FATAL'])
        optreg('user', 'Set username to run server as. This option has no '
               'effect if server is started in foreground.', 'u', 
               argument=True, default=ServerApp.DEFAULT_USER)
        optreg('pidfile', 'Set file to store PID in. This option has no '
               'effect if server is started in foreground.', 'p', 
               argument=True, default=ServerApp.DEFAULT_PIDFILE)
    
    def initialize(self, force=False):
        self.log.info('Initializing database.')
        dbtype = self.config.get('database', 'type',
                                 ServerApp.DEFAULT_DB_TYPE)

        # SQLite specific fixup: delete empty file if existant.
        if dbtype == 'sqlite':
            dbfile = self.config.get('database', 'database', 
                                     ServerApp.DEFAULT_DB_DB)

            if os.path.exists(dbfile) and os.stat(dbfile)[stat.ST_SIZE] == 0:
                # delete if zero-sized
                os.unlink(dbfile)

        self.drop_privileges()

        # Per-database type initialization
        if dbtype == 'sqlite' or force:
            self.init_db()
            create_tables()

        # Warn the user that nothing has happened.
        else:
            print 'Initialization of database with type %s not possible.' \
                % (dbtype)

        if dbtype == 'sqlite':
            dbfile = self.config.get('database', 'database', 
                                     ServerApp.DEFAULT_DB_DB)
            # Fix file permissions.
            os.chmod(dbfile, stat.S_IRUSR|stat.S_IWUSR)

        # After DB initialization we have to do crypto initialization.
        if not force or not self.root_command.option_is_set('foreground'):
            self.log.info('Crypto initialization is only done if --force-init '
                          'and --foreground are present.')
            self.log.info('If crypto is (re-)initialized all clients will have'
                          ' to be re-initialized as well!')
        else:
            self.log.info('Crypto initialization is starting.')
            self.init_crypto(fail=False)
        
            self.cryptoHelper.init_crypto()

        self.exit(0)

    def init_db(self):
        self.log.debug("INIT: database.")
        # get settings from config file
        db_type = self.config.get('database', 'type',
                                 ServerApp.DEFAULT_DB_TYPE)
        db_host = self.config.get('database', 'host')
        db_database = self.config.get('database', 'database', 
                                      ServerApp.DEFAULT_DB_DB)
        db_user = self.config.get('database', 'user')
        db_password = self.config.get('database', 'password')

        # generate connection string
        self.db_connstring = db_type + '://'
        if db_user and db_host:
            self.db_connstring += db_user
        if db_user and db_password and db_host:
            self.db_connstring += ':' + db_password + '@'
        if db_host:
            self.db_connstring += db_host
        self.db_connstring += '/' + db_database

        # Check file permissions of sqlite database file.
        if db_type == 'sqlite':
            self.check_file_security(db_database, allow_group=True)

        db_bind(self.db_connstring)
        self.log.debug("INIT: database -> OK")

    def drop_privileges(self):
        user = self.root_command.option_get_value('user')
        data = pwd.getpwnam(user)
        pw_uid = data[2]
        pw_gid = data[3]

        try:
            os.setegid(pw_gid)
            os.seteuid(pw_uid)
        except OSError, e:
            self.log.error('Could not drop privileges: ' + e.errno + ' ' +
                           e.strerror)
            self.exit(255)

        self.log.info("Running as user '" + user + "'.")

    def write_pidfile(self, pid):
        try:
            fp = open(self.pid_file_path, 'w')
            fp.write(pid)
            fp.close()
        except IOError, e:
            print 'Failed to write PID file (%s).' % (e)
            app.exit(255)

    def daemonize(self):
        sys.stdout.flush()
        sys.stderr.flush()
        # Credits:
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012 

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            print >>sys.stderr, 'Early forking failed: %s (%d)' % (e.errno, 
                                                                   e.strerror)
            sys.exit(1)

        # avoid preventing unmounting
        os.chdir('/')
        os.setsid()
        os.umask(0)

        errorlog = file(self.error_log_path, 'a+')
        stderr_old = file(self.error_log_path, 'a+')

        os.dup2(sys.stderr.fileno(), stderr_old.fileno())
        os.dup2(errorlog.fileno(), sys.stdout.fileno())
        os.dup2(errorlog.fileno(), sys.stderr.fileno())
        os.dup2(errorlog.fileno(), sys.stdin.fileno())

        try:
            pid = os.fork()
            if pid > 0:
                print 'nwu-server now running as %d' % (pid)
                self.write_pidfile()
            sys.exit(0)
        except OSError, e:
            print >> stderr_old, 'late fork failed: %s (%d)' % (e.errno,
                                                               e.strerror)
            sys.exit(1)
    
    def init_logging(self, daemon=False):
        if daemon:
            try:
                formatter = logging.Formatter('nwu-server[%(process)d] '
                                              '%(levelname)s %(message)s')
                hdlr = logging.handlers.SysLogHandler(
                    '/dev/log', 
                    facility = logging.handlers.SysLogHandler.LOG_DAEMON)
            except socket.error:
                print 'Error while connecting log instance to syslog. Is the '\
                    'syslog daemon running?'
                sys.exit(1)

        else:
            hdlr = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s (%(levelname)s): '
                                          '%(message)s')
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)
        loglevel = self.root_command.option_get_value('loglevel')
        self.log.setLevel(eval('logging.' + loglevel))

    def init_server(self):
        host = self.config.get('webservice', 'host', 
                               ServerApp.DEFAULT_SERVER_HOST)

        port = self.config.get('webservice', 'port',
                               ServerApp.DEFAULT_SERVER_PORT)
        try:
            port = int(port)
        except ValueError:
            self.log.error('Invalid server port: %s' % (port))
            self.exit(255)

        try:
            self.server = Server(host, port, self)
            self.log.info('Starting nwu-server. Listening at %s:%d.'\
                              % (host, port))
            self.server.serve_forever()
        except:
            self.log.error(traceback.format_exc())

    def exit(self, code):
        if self.log:
            self.log.info('Server exiting (%d).' % (code))
        else:
            print 'Server exiting (%d).' % (code)
        sys.exit(code)
                   

    def crypto_try_load_key(self, path):
        # This intentionally raises an exception on error.
        fp = open(path, 'r')
        key = X509PrivateKey(fp.read())
        fp.close()


    def crypto_try_load_cert(self, path):
        # This intentionally raises an exception on error.
        fp = open(path, 'r')
        cert = X509Certificate(fp.read())
        fp.close()
    
    def check_file_security(self, path, allow_group=False):
        ''' Checks whether a file's permissions are secure. '''
        try:
            statres = os.stat(path)
        except OSError, e:
            return True

        mode = statres[stat.ST_MODE]

        if not allow_group:
            if (mode & stat.S_IRGRP) > 0 or (mode & stat.S_IWGRP) > 0 or \
                    (mode & stat.S_IXGRP) > 0:
                raise Exception('Security violation: %s is group-accessible.' 
                                % (path))

        if (mode & stat.S_IROTH) > 0 or (mode & stat.S_IWOTH) > 0 or \
                (mode & stat.S_IXOTH) > 0:
            raise Exception('Security violation: %s is world-accessible.' 
                            % (path))

    def config_path(self, filename):
        # Do not touch absolute paths.
        if filename[0] == '/' or (filename[0] == '.' and filename[1] == '/'): 
            return filename
        
        return os.path.join(self.config.get(
                'general', 'configbase', ServerApp.DEFAULT_CONFIG_BASE),
                            filename)
                                            

    def init_crypto(self, fail=True):
        # Load crypto-specific files.
        try:
            self.ca_cert = self.config_path(self.config.get(\
                    'crypto', 'cacert', ServerApp.DEFAULT_CA_CERT))
            self.ca_key = self.config_path(self.config.get(\
                    'crypto', 'cakey', ServerApp.DEFAULT_CA_KEY))
            # XXX: Unused for now.
            self.ca_crl = self.config_path(self.config.get(\
                    'crypto', 'cacrl', ServerApp.DEFAULT_CA_CRL))
            self.ca_serial = self.config_path(self.config.get(\
                    'crypto', 'caserial', ServerApp.DEFAULT_CA_SERIAL))
            self.server_cert = self.config_path(self.config.get(\
                    'crypto', 'servercert', ServerApp.DEFAULT_SERVER_CERT))
            self.server_key = self.config_path(self.config.get(\
                    'crypto', 'serverkey', ServerApp.DEFAULT_SERVER_KEY))

            self.crypto_helper = CryptoHelper(self)

            # Check file permissions on all keys.
            if os.path.exists(self.ca_key):
                if os.path.islink(self.ca_key):
                    raise Exception('Security violation: CA key is a symlink.')

                self.check_file_security(self.ca_key)
                

            if os.path.exists(self.server_key):
                if os.path.islink(self.server_key):
                    raise Exception('Security violation: Server key is a'
                                    'symlink.')
                self.check_file_security(self.server_key)

            self.crypto_try_load_cert(self.ca_cert)
            self.crypto_try_load_cert(self.server_cert)
            self.crypto_try_load_key(self.ca_key)
            self.crypto_try_load_key(self.server_key)

            # XXX: verify server key.
        except IOError, e:
            if fail:
                self.log.error('Could not initialize crypto: %s' % (e))
                self.exit(255)
        except Exception, e:
            self.log.error('Error during crypto init: %s' % (e))
            self.exit(255)

