#!/usr/bin/env python
from distutils.core import setup
setup(name='Nwu',
      version='0.1.7',
      description='Network-wide Updates',
      author='Yves Junqueira',
      author_email='yves@cetico.org',
      maintainer='Yves Junqueira',
      maintainer_email='yves@cetico.org',
      url='http://cetico.org/nwu',
      scripts=['bin/nwu-agent', 'bin/nwu-maint', 
       'bin/nwu', 'bin/nwu-server'],
      packages=['nwu', 'nwu.common',
                'nwu.agent', 'nwu.server', 'nwu.server.db',
                'nwu.sysinfo', 'nwu.sysinfo.linux']
#      data_files=[('/etc/nwu', ['nwu-agent/sample_conf/agent.conf']),
#                  ('/etc/nwu', ['nwu-server/sample_conf/server.conf']),
#		  ('/usr/share/doc/nwu-server', ['nwu-server/README']),
#		  ('/usr/share/doc/nwu-agent', ['nwu-agent/README'])]
     )
