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
import os
import socket
import stat
import sys

from nwu.common import certtool
from nwu.common.app import Application, Command
from nwu.common.rpc import RPCProxy, NotPossibleFault, NotFoundFault, Fault
from nwu.common.rpc import UnknownMethodFault
from nwu.common.scheduler import Scheduler, RecurringTask
from nwu.common.gnutlsext import X509Certificate, X509PrivateKey

class AgentCertFetcherTask(RecurringTask):
    def __init__(self, app):
        self.proxy = app.proxy
        self.app = app
        self.log = app.log
        RecurringTask.__init__(self, 'CertFetcher', app.poll_interval)

    def execute(self):
        """ Try to fetch our client certificate from the server. """
        cert = None
        try:
            self.log.debug("Trying to fetch certificate for account id %s." % (self.app.account_id))
            cert = self.proxy.anon.get_certificate(self.app.account_id)
        except NotFoundFault, f:
            self.log.error('Account with ID %d not found at server.' \
                          % (app.account_id))
            sys.exit(1)
        except NotPossibleFault, f:
            # Account not yet present
            self.log.info('No certificate present on server yet.')
        except Fault, f:
            self.log.error('Unhandled fault: %s' % (f))
            sys.exit(1)
        
        if cert:
            self.app.scheduler.stop()
            self.app.scheduler.remove_all_tasks()
            self.app.save_certificate(cert)
            self.app.reinit_proxy()
            self.app.run()
            return True
        return False

class AgentRootCommand(Command):
    def execute(self, app, args, cmd_name=None):
        self.log = app.log

        if len(args) > 0 or cmd_name:
            if cmd_name:
                arg = cmd_name
            else:
                arg = args[0]

            self.show_help(app, message='Unknown option: %s' % (arg))
            app.exit(255)

        if self.option_is_set('configbase'):
            app.config_base = os.path.expanduser(self.option_get_value('configbase'))

        app.config_file_path = os.path.expanduser(self.option_get_value('configfile'))
        
        app.init_logging(not self.option_is_set('foreground'))

        app.read_config()

        app.server_uri = app.config.get('connection', 'server_uri', 
                                        app.DEFAULT_SERVER_URI)

        app.proxy = RPCProxy(app.server_uri)

        app.ca_cert_path = app.config.get('crypto', 'cacert', 
                                          app.config_path(app.DEFAULT_CA_CERT))
        app.client_cert_path = app.config.get(
            'crypto', 'cert', app.config_path(app.DEFAULT_CLIENT_CERT))
        app.client_key_path = app.config.get(
            'crypto', 'key', app.config_path(app.DEFAULT_CLIENT_KEY))
        app.account_id = app.config.get(
            'agent', 'id', None)
        
        if app.account_id:
            try:
                app.account_id = int(app.account_id)
            except:
                self.log.fatal('Account ID could not be converted to integer: %s' % (app.account_id))
                sys.exit(255)

        app.poll_interval = app.config.get(
            'agent', 'pollinterval', app.DEFAULT_POLLINTERVAL)

        if self.option_is_set('initialize'):
            app.initialize()

        if not app.account_id:
            self.log.fatal('Agent not initialized yet.')
            sys.exit(255)

        if not self.option_is_set('foreground'):
            app.daemonize()
        
        app.run()

class AgentApp(Application):
    # DEFAULT SETTINGS
    DEFAULT_CONFIG_BASE = '/etc/nwu/'
    DEFAULT_CONFIG = '/etc/nwu/agent.conf'
    DEFAULT_CA_CERT = 'ca.crt'
    DEFAULT_CLIENT_CERT = 'client.crt'
    DEFAULT_CLIENT_KEY = 'client.key'
    DEFAULT_PIDFILE = '/var/run/nwu/nwu-agent.pid'
    DEFAULT_LOGLEVEL = 'INFO'
    DEFAULT_ERRORLOG = '/dev/null'
    DEFAULT_POLLINTERVAL = 30
    DEFAULT_SERVER_URI = 'https://localhost:8088'

    def __init__(self, args=sys.argv[1:], bin_name=sys.argv[0]):
        self.foreground = False
        self.config_base = AgentApp.DEFAULT_CONFIG_BASE
        self.client_key = None
        self.client_cert = None
        self.server_uri = None
        
        Application.__init__(self, args, bin_name,
                             root_command_class=AgentRootCommand)
        self.log = logging.getLogger()

        optreg = self.root_command.register_option
        optreg('configfile', 'Specify the config file to read options from.',
               'c', argument=True, default=AgentApp.DEFAULT_CONFIG)
        optreg('initialize', 'Initialize agent and exit.', 'i')
        optreg('foreground', 'Start agent in foreground.', 'f')
        optreg('errorlog', 'Set file to send untreated python errors to', 'e',
               argument=True, default=AgentApp.DEFAULT_ERRORLOG)
        optreg('loglevel', 'Set verbosity.', 'l', argument=True,
               default=AgentApp.DEFAULT_LOGLEVEL,
               valid_values=['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR',
                             'FATAL'])
        optreg('pidfile', 'Set file to store PID in. This option has no'
               'effect if the agent is started in foreground.', 'p',
               argument=True, default=AgentApp.DEFAULT_PIDFILE)
        optreg('pollinterval', 'Set the polling interval.', 't',
               default=AgentApp.DEFAULT_POLLINTERVAL)
        optreg('configbase', 'Set configuration file base directory.', 'b',
               default=AgentApp.DEFAULT_CONFIG_BASE)

    def daemonize(self):
        """ Fork and continue running in background. """
        sys.stdout.flush()
        sys.stderr.flush()
        # Credits:                                                             
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012 

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

        except OSError, e:
            print >>sys.stderr, 'Forking failed: %s (%d)' % (e.errno,
                                                             e.strerror)
            sys.exit(1)

        os.chdir('/')
        os.setsid()
        os.umask(0)
        
        error_log = file(self.error_log_path, 'a+')
        stderr_old = file(self.error_log_path, 'a+')

        os.dup2(sys.stderr.fileno(), stderr_old.fileno())
        os.dup2(errorlog.fileno(), sys.stdout.fileno())
        os.dup2(errorlog.fileno(), sys.stderr.fileno())
        os.dup2(errorlog.fileno(), sys.stdin.fileno())

        try:
            pid = os.fork()
            if pid > 0:
                print 'nwu-agent now running as %d' % (pid)
                self.write_pidfile()

            sys.exit(0)

        except OSError, e:
            print >> stderr_Old, 'late fork failed: %s (%d)' % (e.errno,
                                                                e.strerror)
            sys.exit(1)

    def init_crypto(self):
        """ Crypto initialization """
        # Both the CA certificate and the client key are mandatory
        try:
            ca_cert_data = open(self.ca_cert_path, 'r').read()
            client_key_data = open(self.client_key_path, 'r').read()
            self.ca_cert = X509Certificate(ca_cert_data)
            self.client_key = X509PrivateKey(client_key_data)
        except Exception, e:
            # We need to catch all exceptions here, including GnuTLS ones.
            self.log.error('Client not initialized yet: %s' % (e))
            sys.exit(1)
        
        # The client certificate is optional.
        try:
            client_cert_data = open(self.client_cert_path, 'r').read()
            self.client_cert = X509Certificate(client_cert_data)
        except Exception, e:
            self.log.debug('Could not load client certificate: %s' % (e))
            self.client_cert = None
            if not self.account_id:
                self.log.error('Client not initialized yet: '\
                                   'Unknown account ID.')
                sys.exit(1)

    def init_logging(self, daemon=False):
        if daemon:
            try: 
                formatter = logging.Formatter('nwu-agent[%(process)d] '
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

    def run(self):
        """ Agent main runner """
        # Create our scheduler...
        self.scheduler = Scheduler(self)
        # Check if we do have a valid certificate
        if not self.client_cert:
            cert_fetcher = AgentCertFetcherTask(self)
            self.log.info("Executing certificate fetcher.")
            if not cert_fetcher.execute():
                self.log.info("No certificate received, scheduling fetcher task.")
                self.scheduler.add_task(AgentCertFetcherTask(self))
            else:
                self.log.info("Certificate received.")
        else:
            # XXX: Place all tasks the client should do right here.
            self.scheduler.add_task(AgentPackageSyncTask(self))

        self.log.info('Scheduler started.')
        # There is no need to run the scheduler in a separate thread here.
        # That's why we can safely call self.scheduler.run().
        self.scheduler.run()
        self.log.info('Scheduler stopped.')

    def initialize(self, force=False):
        """ Initialize agent configuration """
        # step 0: Download CA certificate from server.
        # XXX: Check if certificate in self.ca_cert_path is valid
        #
        # Do not download certificate if one is already present and force is False
        if force or not os.path.exists(self.config_path(self.ca_cert_path)):
            try:
                cacert = self.proxy.anon.get_ca_certificate()
            except Fault, f:
                self.log.fatal('Unhandled fault: %s' % (f))
                sys.exit(255)

            self.log.debug('Received CA certificate from server.')

            if not cacert:
                self.log.error('Received CA certificate with None-value.')
                sys.exit(1)

            try:
                ca_cert_path = self.config_path(self.ca_cert_path)
                self.log.debug('Writing CA certificate to %s.' % (ca_cert_path))
                if os.path.exists(ca_cert_path):
                    os.chmod(ca_cert_path, stat.S_IWUSR)
                fp = open(ca_cert_path, 'w')
                fp.write(cacert)
                fp.close()
                os.chmod(ca_cert_path, stat.S_IRUSR)

                self.log.debug('CA certificate written.')
            except IOError, e:
                self.log.error('Initialization failed: %s' % (e))
                sys.exit(255)

        # step 1: Generate private key.
        # Do not generate private key if key is present and force is False
        #
        # XXX: Check if data in self.client_key_path is valid.
        if force or not os.path.exists(self.config_path(self.client_key_path)):
            self.log.info('Generating private key. This could take some time.')
            key = certtool.generate_privkey()
            try:
                fp = open(self.config_path(self.client_key_path), 'w')
                fp.write(key)
                fp.close()
                os.chmod(self.config_path(self.client_key_path), stat.S_IRUSR)
            except IOError, e:
                self.log.error('Initialization failed: %s' % (e))
                sys.exit(255)
        else:
            key = open(self.config_path(self.client_key_path), 'r').read()
            self.log.info('Not generating new private key; using existing one.')

        # step 2: Ask server to sign CSR.
        hostname = socket.gethostname()
        country = raw_input('Please enter a 2-character identifier for the '\
                                'country this system is located at: ')
        org = raw_input('Please enter the name of your organization: ')

        # XXX: Ask user if input is correct, just like in 
        #      nwu.server.app.CryptoHelper.
        # XXX: Use nwu.common.gnutlsext instead of certtool.
        csr = certtool.generate_csr(key, country, org, hostname)

        # step 3: Send CSR to server.
        try:
            account_id = self.proxy.anon.request_csr_signing(hostname, csr)
        except NotPossibleFault, e:
            self.log.error('The server reported an error: %s' % (e))
            sys.exit(255)
        except Fault, f:
            self.log.fatal('Unhandled fault: %s' % (f))
            sys.exit(255)
        
        self.log.info('Sent CSR to server for signing.')
        self.log.debug('Received our account ID: %s' % (account_id))

        self.config.set('agent', 'id', str(account_id))

        try:
            fp = open(self.config_file_path, 'w')
            self.config.write(fp)
            fp.close()
        except IOError, e:
            self.log.error('Could not save config file: %s' % (e))
            sys.exit(1)

        self.log.info('Finished initialization sequence.')
        sys.exit(0)
    
    def save_certificate(self, cert):
        """ Save certificate to file. """
        try:
            fp = open(self.client_cert_path, 'w')
            fp.write(cert)
            fp.close()
        except IOError, e:
            self.log.error('Could not save certificate: %s' % (e))
            sys.exit(1)

    def reinit_proxy(self):
        self.init_crypto()
        self.proxy = RPCProxy(self.server_uri,
                              key_file=self.client_key_path,
                              cert_file=self.client_cert_path,
                              ca_cert_file=self.ca_cert_path)
        self.log.info('Proxy re-initialized.')

    def config_path(self, file):
        """ Prefix filename with config base """
        return os.path.join(self.config_base, file)

