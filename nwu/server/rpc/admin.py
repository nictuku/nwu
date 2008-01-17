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

from nwu.common.rpc import NotFoundFault
from nwu.server.rpc import RPCHandler, PRIV_ADMIN

class AdminHandler(RPCHandler):
    # TODO: Add logging to all handlers
    def __init__(self, app):
        RPCHandler.__init__(self, app, PRIV_ADMIN)
        self.cryptoHelper = app.cryptoHelper

    def get_computer_info(self, account, remote_host, computer_id):
        """ Get computer information for given computer or all computers
        if computer_id is None.
        """
        computers = []

        # Get info for all computers.
        if not computer_id:
            comps = Computer.query.all()
        else:
            comps = [Computer.get(computer_id)]

        for c in comps:
            computers.append(c.to_dict())

        return computers

    def get_computer_tasks(self, account, remote_host, computer_id):
        """ Get all tasks for given computer. """
        comp = Computer.get(computer_id)

        if comp == None:
            raise NotFoundFault('Computer with id %s' % (computer_id))

        tasks = []

        for t in comp.tasks:
            tasks.append(t.to_dict())
        
        return tasks

    def get_current_packages(self, account, remote_host, computer_id,
                             package_name):
        """ Get current packages with package name (wildmask) for given
        computer.
        """
        comp = Computer.get(computer_id)

        if comp == None:
            raise NotFoundFault('Computer with id %s' % (computer_id))

        # Wildcard support
        package_name = package_name.replace('*', '%')
        packages = comp.current_packages.name.like(package_name)
        result = []
        for p in packages:
            result.append(p.to_dict())

        return result

    def get_update_candidates(self, account, remote_host, computer_id,
                              package_name):
        """ Get update candidates with given package name (wildmask)
        for given computer.
        """
        comp = Computer.get(computer_id)

        if not comp:
            raise NotFoundFault('Computer with id %s' % (computer_id))

        # Wildcard support
        package_name = package_name.replace('*', '%')
        cands = comp.update_candidates.name.like(package_name)
        result = []
        for c in cands:
            result.append(c.to_dict())

        return result

    def get_repositories(self, account, remote_host, computer_id, type,
                         uri):
        """ Get repositories of given type, with given uri (wildmask)
        of given computer.
        """
        comp = Computer.get(computer_id)

        if not comp:
            raise NotFoundFault('Computer with id %s' % (computer_id))

        # Wildcard support
        uri = uri.replace('*', '%')
        repos = comp.repositories.uri.like(uri).filter_by(type=type)
        result = []

        for r in repos:
            result.append(r.to_dict())

        return result

    def get_account(self, account, remote_host, account_id):
        """ Get account information for given account. """
        ac = Account.get(account_id)
        
        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))

        return ac.to_dict()

    def get_account_id_by_name(self, account, remote_host, account_name):
        """ Get account id for given account name. """
        ac = Account.get_by(name=account_name)

        if not ac:
            raise NotFoundFault('Account with name %s' % (account_name))
        return ac.oid

    def get_account_ids(self, account, remote_host):
        """ Get all account ids. """
        acs = Account.query.all()

        result = []

        for ac in acs:
            result.append(ac.oid)

        return result

    def delete_account(self, account, remote_host, account_id):
        """ Delete account """
        # XXX: We might want to consider deactivating accounts instead
        #      of actually deleting them from the database.
        ac = Accoung.get(account_id)

        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))

        ac.delete()
        ac.flush()
        return True

    def set_privilege(self, account, remote_host, account_id, privilege):
        """ Set privilege on an account. """
        ac = Account.get(account_id)

        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))

        # TODO: do we want some sort of protection against removing/adding
        #       admins?

        ac.privilege = privilege
        ac.save()
        ac.flush()

        return True

    def get_csr(self, account, remote_host, account_id):
        """ Get CSR for specified account. """
        ac = Account.get(account_id)

        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))
        
        return ac.csr

    def sign_csr(self, account, remote_host, account_id):
        """ Create certificate from CSR """
        ac = Account.get(account_id)

        if not ac:
            raise NotFoundFault('Account with id %s' % (account_id))

        ac.cert = self.cryptoHelper.sign_csr(ac.csr)
        ac.save()
        ac.flush()

        return True

    def add_task(self, account, remote_host, computer_id, task_name,
                 task_details):
        """ Add new task for computer. """
        
        c = Computer.get(computer_id)
        
        if not c:
            raise NotFoundFault('Computer with id %s' % (computer_id))

        t = Task(computer=c, action=task_name, details=task_details)
        t.save()
        t.flush()
