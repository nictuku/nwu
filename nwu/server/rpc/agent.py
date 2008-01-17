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

from nwu.server.db.model import Computer, UpdateCandidates, Repositories
from nwu.server.db.model import CurrentPackages, TablesVersion, delete_all
from nwu.server.rpc import RPCHandler, PRIV_AGENT
from nwu.common.rpc import NotFoundFault, InvalidParamsFault

class AgentHandler(RPCHandler):
    def __init__(self, app):
        RPCHandler.__init__(self, app, PRIV_AGENT)

    def _get_computer_from_account(self, account):
        """ Helper method: Convert account to computer, raise Fault if no
        corresponding computer exists.
        """
        if not account.computer:
            raise NotFoundFault('Account is not associated to a computer '
                                'record.')
        return account.computer

    def _increment_tables_version(self, computer, table_name):
        """ Helper method: Increment version of given table for
        given computer.
        """
        table = computer.tables_version.get_by(name=table_name)
        if not table:
            table = TablesVersion(name=table_name, computer=computer, 
                                  version=0)
        else:
            table.version = table.version + 1
        table.save()
        table.flush()

    def _delete_tables_version(self, computer, table_name):
        """ Helper method: Delete version information of given table
        for given computer.
        """
        table = computer.tables_version.get_by(name=table_name)
        if table:
            table.delete()
            table.flush()

    def create_computer(self, account, remote_host, hostname, os_name,
                        os_version):
        """Create computer in database (and link it to the account of the
        creator).

        Returns the computer id.
        """
        # XXX: Add logging.

        if not type(hostname) == str or not type(os_name) == str \
                or not type(os_version) == str:
            raise InvalidParamsFault('create_computer')

        if account.computer:
            raise NotPossibleFault('Account already associated with a computer'
                                   'record.')

        c = Computer(hostname=hostname, os_name=os_name, os_version=os_version)
        c.save()
        c.flush()

        return c.oid

    def get_computer_id(self, account, remote_host):
        """ Get own computer id. """
        c = self._get_computer_from_account(account)

        return account.computer.oid

    def get_table_checksum(self, account, remote_host, table_name):
        """ Return table checksum for given table. """
        c = self._get_computer_from_account(account)

        if type(table_name) != str:
            raise InvalidParamsFault('get_table_checksum')

        table_version = c.tables_version.get_by(name=table_name)

        if not table_version:
            raise NotFoundFault('TableVersion with name %s' % (table_name))

        return table_version.version
        
    def get_tasks(self, account, remote_host):
        """ Get assigned tasks. """
        c = self._get_computer_from_account(account)
        result = []
        for t in c.tasks:
            result.append(t.to_dict())
        return result

    def set_update_candidates(self, account, remote_host, update_candidates):
        """ Remove old update candidates and set new ones. """
        c = self._get_computer_from_account(account)

        delete_all(c.update_candidates)

        if type(update_candidates) != list:
            raise InvalidParamsFault('set_update_candidates')

        for uc in update_candidates:
            if type(uc) != dict or not 'name' in uc or not 'version' in uc:
                raise InvalidParamsFault('set_update_candidates')

            name = c['name']
            version = c['version']
            u = UpdateCandidates(computer=c, name=name, version=version)
            u.save()
            u.flush()

    def update_current_packages(self, account, remote_host, packages_add,
                                packages_remove):
        """ Add and/or remove packages from current_packages table. """
        c = self._get_computer_from_account(account)

        if type(packages_remove) != list or type(packages_add) != list:
            raise InvalidParamsFault('update_current_packages')

        # First remove the packages.
        for name in packages_remove:
            package = c.current_packages.get_by(name=name)
            if package:
                package.delete()
                package.flush()
    
        # Now add the new ones.
        for p in packages_add:
            if type(p) != dict or not 'name' in p or not 'version' in p:
                raise InvalidParamsFault('update_current_packages')

            name = p['name']
            version = p['version']

            package = CurrentPackages(computer=c, name=name, version=version)
            package.save()
            package.flush()
        self._increment_tables_version(c, 'current_packages')

    def update_update_candidates(self, account, remote_host, packages_add,
                                 packages_remove):
        """ Add and/or remove packages from the update_candidates table. """
        c = self._get_computer_from_account(account)

        if type(packages_add) != list or type(packages_remove) != list:
            raise InvalidParamsFault('update_update_candidates')

        # First remove the packages.
        for name in packages_remove:
            package = c.update_candidates.get_by(name=name)
            if package:
                package.delete()
                package.flush()

        # Now add the new ones.
        for p in packages_add:
            if type(p) != dict or not 'name' in p or not 'version' in p:
                raise InvalidParamsFault('update_update_candidates')
            name = p['name']
            version = p['version']
            package = UpdateCandidates(computer=c, name=name, version=version)
            package.save()
            package.flush()
        self._increment_table_version(c, 'update_candidates')
            
    def set_repositories(self, account, remote_host, repositories):
        """ Set new repository list. """
        c = self._get_computer_from_account(account)

        if type(repositories) != list:
            raise InvalidParamsFault('set_repositories')

        delete_all(c.repositories)

        for r in repositories:
            if type(r) != dict or not 'filename' in r or not 'type' in r \
                    or not 'uri' in r or not 'distribution' in r \
                    or not 'components' in r:
                raise InvalidParamsFault('set_repositories')
            filename = r['filename']
            type = r['type']
            uri = r['uri']
            dist = r['distribution']
            components = r['components']
            
            repository = Repositories(filename=filename, type=type, uri=uri,
                                      distribution=dist, components=components)
            repository.save()
            repository.flush()
    
        self._increment_tables_version('repositories')

    def wipe_update_candidates(self, account, remote_host):
        """ Remove all entries from update_candidates table and reset table
        version.
        """
        c = self._get_computer_from_account(account)

        delete_all(c.update_candidates)

        self._delete_tables_version(c, 'update_candidates')

    def wipe_current_packages(self, account, remote_host):
        """ Remove all entries from current_packages table and reset
        table version.
        """

        c = self._get_computer_from_account(account)

        delete_all(c.current_packages)

        self._delete_tables_version(c, 'current_packages')

    def wipe_repositories(self, account, remote_host):
        """ Remove all entries from repositories table and reset
        table version.
        """
        
        c = self._get_computer_from_account(account)

        delete_all(c.repositories.delete)

        self._delete_tables_version(c, 'repositories')
