# From sqlobject 0.6, licensed under the LGPL
from threading import local
import logging
log = logging.getLogger("nwu_server.db.backport")

class ConnectionHub(object):

    """
    This object serves as a hub for connections, so that you can pass
    in a ConnectionHub to a SQLObject subclass as though it was a
    connection, but actually bind a real database connection later.
    You can also bind connections on a per-thread basis.

    You must hang onto the original ConnectionHub instance, as you
    cannot retrieve it again from the class or instance.

    To use the hub, do something like::

        hub = ConnectionHub()
        class MyClass(SQLObject):
            _connection = hub

        hub.threadConnection = connectionFromURI('...')

    """

    def __init__(self):
        self.threadingLocal = local()

    def __get__(self, obj, type=None):
        # I'm a little surprised we have to do this, but apparently
        # the object's private dictionary of attributes doesn't
        # override this descriptor.
        if obj and obj.__dict__.has_key('_connection'):
            return obj.__dict__['_connection']
        return self.getConnection()

    def __set__(self, obj, value):
        obj.__dict__['_connection'] = value

    def getConnection(self):
        try:
            return self.threadingLocal.connection
        except AttributeError:
            try:
                return self.processConnection
            except AttributeError:
                raise AttributeError(
                    "No connection has been defined for this thread "
                    "or process (conn hub)")

    def doInTransaction(self, func, *args, **kw):
        """
        This routine can be used to run a function in a transaction,
        rolling the transaction back if any exception is raised from
        that function, and committing otherwise.

        Use like::

            sqlhub.doInTransaction(process_request, os.environ)

        This will run ``process_request(os.environ)``.  The return
        value will be preserved.
        """
        # @@: In Python 2.5, something usable with with: should also
        # be added.
        old_conn = self.getConnection()
        conn = old_conn.transaction()
        self.threadConnection = conn
        try:
            try:
                value = func(*args, **kw)
            except:
                conn.rollback()
                raise
            else:
                conn.commit()
                return value
        finally:
            self.threadConnection = old_conn

    def _set_threadConnection(self, value):
        self.threadingLocal.connection = value

    def _get_threadConnection(self):
        return self.threadingLocal.connection

    def _del_threadConnection(self):
        del self.threadingLocal.connection
        #log.info("delando conn")

    threadConnection = property(_get_threadConnection,
                                _set_threadConnection,
                                _del_threadConnection)
