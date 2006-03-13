#!/usr/bin/env python
"""Gets nwu nodes data from a local database.
This will be replaced by rpc_data.py sometime.
"""

import sys
# svn test only
sys.path.append('../nwu-server')
from nwu_server.db.operation import *

class nwu_data:

    nodes = None
    tasks = None 

    def __init__(self):

        m = machine.select()
        self.nodes = list(m)

        t = task.select()
        self.tasks = list(t)

    class task(machine, task):
        def __init__(self):
            pass
        
        def append(self, new_task):

            machine_id = new_task['machine_id']
            task_name = new_task['task_name']

            if new_task.has_key('task_detail'):
                task_detail = new_task['task_detail']
            else:
                task_detail = None
       
            m = machine.select(machine.q.id==machine_id)
            ma = list(m)
            for mach in ma:
                print "Found machine id=" + machine_id + " in the database. Requesting " + task_name + \
                    str(task_detail) + "."
                t = task(machine=machine_id, action=task_name,details=task_detail)

