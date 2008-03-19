#!/usr/bin/python
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

from threading import Thread, Lock, Event
from time import time

class Task:
    """ Task base class. """
    TYPE_ONESHOT = 0
    TYPE_RECURRING = 1

    def __init__(self, name, type, exec_time):
        self.name = name
        self.type = type
        self.exec_time = exec_time

    def execute(self):
        """ Method that is executed by the scheduler.

        Override to add your own code.
        """
        pass

class RecurringTask(Task):
    """ A recurring task.

    Is executed all <interval> seconds"""
    def __init__(self, name, interval):
        self.interval = interval
        Task.__init__(self, name, Task.TYPE_RECURRING, int(time())+interval)

class OneshotTask(Task):
    """ A one shot task.

    Is executed at <exec_time>.
    """
    def __init__(self, name, exec_time):
        Task.__init__(self, name, Task.TYPE_ONESHOT, exec_time)

class Scheduler(Thread):
    """ Manages scheduled tasks """
    def __init__(self, app, name='Scheduler'):
        Thread.__init__(self)
        self.setName(name)
        self.app = app
        self.log = app.log
        self.tasks = []
        self.taskLock = Lock()
        self.exitEvent = Event()

    def init_thread(self):
        """ Custom thread initialization code.
        
        This method can be overridden to, for example, establish
        a database connection.
        """
        pass

    def stop(self):
        """ Stop the Scheduler. """
        self.log.debug("scheduler: stopped.")
        self.exitEvent.set()

    def add_task(self, task):
        """ Add a task to the scheduler """
        if self.exitEvent.isSet():
            return False
        self.taskLock.acquire()
        self.tasks.append(task)
        self.taskLock.release()
        self.log.debug("scheduler: task added: %s" % (task.name))
        return True

    def remove_all_tasks(self):
        """ Removes all tasks from the scheduler """
        self.taskLock.acquire()
        self.tasks = []
        self.taskLock.release()
        self.log.debug("scheduler: all tasks removed.")

    def remove_task(self, task):
        """ Remove a task from the scheduler """
        if self.exitEvent.isSet():
            return False
        self.taskLock.acquire()
        self.tasks.remove(task)
        self.taskLock.release()
        self.log.debug("scheduler: task removed: %s" % (task.name))
        return True

    def run(self):
        """ Thread main loop. """
        self.init_thread()

        self.log.debug("scheduler: main loop started.")
        while not self.exitEvent.isSet():
            exec_tasks = []
            
            # Keep lock time as short as possible!
            self.taskLock.acquire()
            for ac in self.tasks:
                if ac.exec_time <= int(time()):
                    exec_tasks.append(ac)
            self.taskLock.release()
            
            for ac in exec_tasks:
                try:
                    self.log.debug("scheduler: executing task %s" % (ac))
                    ac.execute()
                except Exception, e:
                    self.log.warning("scheduler: task %s raised exception: %s" % (ac.name, e))
                if ac.type == Task.TYPE_RECURRING:
                    ac.exec_time = int(time()) + ac.interval

            self.taskLock.acquire()
            for ac in exec_tasks:
                if ac.type == Task.TYPE_ONESHOT:
                    self.tasks.remove(ac)
            self.taskLock.release()

            self.exitEvent.wait(0.1)
        
        # Need to clear event in case of later scheduler re-initialization.
        self.exitEvent.clear()
        
