#!/usr/bin/env python
"""Gets nwu nodes data from a local database.
This will be replaced by rpc_data.py sometime.
"""

import sys
# svn test only
sys.path.append('../nwu-server')
from nwu_server.db.operation import *

class nwu_data:
    """Maintain nwu host data in the database.
    """
    # Make the operations of this class as pythonic as possible
    # Remember another class will be made for xml-rpc but using the same interfaces

    nodes = None
    tasks = None 

    def __init__(self):

        m = machine.select()
        self.nodes = list(m)

        t = task.select()
        self.tasks = list(t)
    
    class machine(machine):
        def __init__(self):
            pass

        # FIXME: move to db/operations.py
        def remove(self, machine_id):

            m = machine.select(machine.q.id==machine_id)
            ma = list(m)
            q = len(ma)
            if q != 1:
                raise Exception, "There are " +  q +  " machine(s) with'" + uniq + "\
        'uniq string and it should have exactly one."

            client_machine = ma[0]

            print "Wiping node "   + client_machine.hostname + '(' + str(client_machine.id) + ')' 

            delquery = conn.sqlrepr(Delete(machine.q, where=\
                (machine.q.id ==  client_machine.id)))

            conn.query(delquery)

    class task(machine, task):
        def __init__(self):
            pass
        
        # FIXME: This would go better in db/operations.py
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

