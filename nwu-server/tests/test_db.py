#   Copyright (C) 2006,2007,2008 Yves Junqueira (yves@cetico.org)
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
 db operations tests

"""
from nwu_server.db.model import metadata, setup_all
from nwu_server.db.model import create_all, session
from nwu_server.db.model import Computer, CurrentPackages, Repositories

def setup():
    metadata.bind = 'sqlite:///'


class TestDb(object):
    # FIXME: os name and version from sysinfo
    def test_base_model(self):
        setup_all()
        create_all()
        one = Computer(hostname='localhost', 
            uniq='32109832109832109831209832190321weee', os_name='Linux',
            os_version='2.6.x', id=1)
        assert one.id == 1
        computer = Computer(hostname='moinmoin',
            uniq='dsadsad1921832918312weee',
            os_name='Linux', os_version='2.6.x')
        session.flush()
        assert computer.id == 2
        CurrentPackages(computer=computer, name='gcc', version='1.1')
        CurrentPackages(computer=computer, name='znes', version='4.1')
        Repositories(computer=computer, filename='/etc/apt/sources.list', 
            type='deb',
            uri='http://blabla', distribution='stable',
            components = 'breezy-updates main restricted')
        session.flush()
        query = Computer.query.filter_by(hostname='localhost').first()
        for package in query.current_packages:
            print package.name, package.version

        for rep in computer.repositories:
            print "REP:", rep.filename + ':' + rep.type, rep.uri,\
                str(rep.components)
        # FIXME: test the repositories
        assert True == True
