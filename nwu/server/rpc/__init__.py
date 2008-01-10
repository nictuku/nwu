#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2008 Stephan Peijnik (yves@cetico.org)
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

from gnutls.crypto import X509Certificate

from nwu.common.rpc import RPCError
from nwu.server.db.model import Account

# Lower number means less privileges.
# 
# There is intentionally some space value-wise between the
# different privileges so finer-grained privilege checks can
# be introduced later on.
# 
# Note that an account having privilege PRIV_ADMIN means that it also holds
# PRIV_AGENT and PRIV_ANONYMOUS.
# 
# The privilege check works like this (pseudo-code):
#
# if client_privilege >= REQUIRED_PRIVILEGE:
#   grant_access
# else:
#   deny_access
PRIV_ANONYMOUS = 0x000
PRIV_AGENT = 0x100
PRIV_ADMIN = 0x200

class RPCResult:
    @staticmethod
    def result(values={}, error=False):
        result = {'error': error}
        result.update(values)
        return result
    
    @staticmethod
    def error(identifier, message):
        return RPCResult.result(values={'error_message': message,
                                        'error_identifier': identifier
                                        }, 
                                error=True)

    @staticmethod
    def unknown_method(method_name):
        return RPCResult.error(
            RPCError.ERR_UNKNOWN_METHOD,
            'Unknown method: %s' % (method_name)
            )
    
    @staticmethod
    def access_denied(method_name):
        return RPCResult.error(
            RPCError.ERR_ACCESS_DENIED,
            'Access to method %s denied.' % (method_name)
            )
    
    @staticmethod
    def not_possible(message):
        return RPCResult.error(
            RPCError.ERR_NOT_POSSIBLE,
            'Operation not possible: %s' % (message)
            )

class RPCHandler:
    def __init__(self, app, required_privilege):
        self.app = app
        self.required_privilege = required_privilege

    def _has_access(self, methodName, held_privilege):
        if held_privilege >= self.required_privilege:
            return True
        return False

class RPCDispatcher:
    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.log = app.log
        self.handlers = {}

        # Check if administrator account is present and privileges are correct.
        admin_cert_file = app.config_path(
            app.config.get('crypto', 'admincert', app.DEFAULT_ADMIN_CERT))
        admin_cert = open(admin_cert_file, 'r').read()

        cert = X509Certificate(admin_cert)
        serial = cert.serial_number

        ac = Account.query.filter_by(cert_serial_number=serial)

        if ac.count() == 0:
            ac = Account(name='root', csr='ROOT_CSR', 
                         cert_serial_number=serial, cert=admin_cert,
                         privileges=PRIV_ADMIN)
            ac.save()
            ac.flush()
        else:
            ac = ac.first()
            if ac.privileges < PRIV_ADMIN:
                ac.privileges = PRIV_ADMIN
                ac.save()
                ac.flush()
        
    def register_handler(self, name, handler, privileges=None):
        self.handlers[name] = handler

    def get_account_info(self, certificate):
        try:
            cert_serial = certificate.serial_number

            acc = Account.query.filter_by(cert_serial_number=cert_serial)

            if acc.count() > 0:
                acc = acc.first()
                return (acc.privileges, acc)

            # Fall-through
        except AttributeError:
            pass
        return (PRIV_ANONYMOUS, None)

    def _dispatch(self, method, params):
        """ Handles authentication and in turn calls the specific methods. """
        # Initially all clients are handled as anonymous ones.
        client_privilege = PRIV_ANONYMOUS
        account_info = None

        # Get client certificate and remove it from the 
        # method parameters.
        client_certificate = params[0]
        params = params[1:]
        
        # All methods are in the form of <handler>.<method>. There are no
        # root-level methods!
        if not '.' in method:
            return RPCResult.unknown_method(method)

        # Get the handler name.
        handlerName, methodName = method.split('.', 2)

        # Do not allow access to methods starting with an underscore!
        if methodName[0] == '_':
            return RPCResult.unknown_method(method)

        # Check if client certificate is present and try getting account
        # information from database.
        if client_certificate:
            client_privilege, account_info = self.get_account_info(
                client_certificate)

        # Re-create params, first parameter is now an Account class (database).
        # WARNING: This may be None for anonymous clients!
        params_new = (account_info,)
        params_new += params
        params = params_new

        if not handlerName in self.handlers:
            return RPCResult.unknown_method(method)

        # Check if user has privileges to call handler's methods...
        handler = self.handlers[handlerName]

        if not handler._has_access(methodName, client_privilege):
            return RPCResult.access_denied(method)

        # First check if the handler has got a _dispatch method.
        # _dispatch should *always* be called instead of the method
        # if present.
        func = getattr(handler, '_dispatch', None)

        if func:
            return handler._dispatch(account_info, methodName, params)

        # Let's find the method to call...
        func = getattr(handler, methodName, None)

        # Graceful failing if method is unknown...
        if not func:
            return RPCResult.unknown_method(method)

        res = func(*params)
        # XXX: Check if res is a valid RPCResult.

        return res
