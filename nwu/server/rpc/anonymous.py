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

from nwu.common.rpc import NotFoundFault, NotPossibleFault
from nwu.server.db.model import Account
from nwu.server.rpc import RPCHandler, PRIV_ANONYMOUS

class AnonymousHandler(RPCHandler):
    def __init__(self, app):
        RPCHandler.__init__(self, app, PRIV_ANONYMOUS)
        self.cacert_data = open(app.ca_cert, 'r').read()
    
    def get_my_privileges(self, account, remote_host):
        priv = 0
        if account:
            priv = account.privileges
        return priv

    def get_ca_certificate(self, account, remote_host):
        return self.cacert_data

    def request_csr_signing(self, account, remote_host, name, csr):
        # TODO: Create some kind of block list to protect us
        #       from spamming (use remote_host).

        # Check if CSR is already present in database.
        ac = Account.query.filter_by(csr=csr)

        if ac.count() > 0:
            raise NotPossibleFault('CSR already present in DB.')

        # Now check if the account name is already taken.
        ac = Account.query.filter_by(name=name)
        if ac:
            raise NotPossibleFault('Account name already taken.')

        ac = Account(name=name, csr=csr, privileges=PRIV_ANONYMOUS)
        ac.save()
        ac.flush()
        
        return ac.oid

    def get_certificate(self, account, remote_host, account_id):
        # Try getting account.
        ac = Account.get(account_id)
        
        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))

        if not ac.cert:
            raise NotPossibleFault('No certificate present for account.')

        return ac.cert
        