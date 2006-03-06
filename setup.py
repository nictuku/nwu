#!/usr/bin/env python
from distutils.core import setup
setup(name='Nwu',
      version='0.1.1',
      description='Network-wide Updates',
      author='Yves Junqueira',
      author_email='yves@cetico.org',
      maintainer='Yves Junqueira',
      maintainer_email='yves@cetico.org',
      url='https://trac.ubuntubrasil.org/nwu/',
      scripts=['nwu-agent/nwu-agent', 'nwu-agent/nwu-maint', 
       'nwu-server/nwu', 'nwu-server/nwu-server'],
      package_dir = {'nwu_agent': 'nwu-agent/nwu_agent', 'nwu_server': 'nwu-server/nwu_server'},
      packages=['nwu_agent', 'nwu_server', 'nwu_server.db'],
     )
