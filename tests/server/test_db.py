#   Copyright (C) 2006-2008 Yves Junqueira (yves@cetico.org)
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
from nwu.server.db.model import *

def setup():
    metadata.bind='sqlite:///'


class TestDb(object):
    # FIXME: os name and version from sysinfo
    def test_base_model(self):
        setup_all()
        create_all()

        one = Computer(hostname='localhost', uniq='32109832109832109831209832190321weee', os_name='Linux', os_version='2.6.x',id=1)
        assert one.id == 1
        m = Computer(hostname='moinmoin', uniq='dsadsad1921832918312weee', os_name='Linux', os_version='2.6.x')
        objectstore.flush()
        assert m.id == 2
        installed = CurrentPackages(computer=m, name='gcc', version='1.1')
        installed = CurrentPackages(computer=m, name='znes', version='4.1')
        reps = Repositories(computer=m, filename='/etc/apt/sources.list',type='deb',
            uri='http://blabla', distribution='stable',
            components = 'breezy-updates main restricted')
        ma = Computer.query.filter_by(hostname='localhost').first()
        for package in ma.current_packages:
            print package.name, package.version

        for rep in ma.repositories:
            print "REP:",rep.filename + ':' + rep.type, rep.uri, str(rep.components)
        assert True == True
        #    help(ma)
            #print ma.aptCurrentPackageses.name, ma.aptCurrentPackageses.version

