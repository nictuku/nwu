#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Defines some RPC used by agents.
"""
from db.operation import *
import os

def create_tables():
    """Creates required tables in the database.
    """
    hub.begin()
    log.debug("Creating necessary tables in the database.")
#    os.unlink('/var/lib/nwu/nwu.db')
    for table in ['computer', 'apt_current_packages', 'apt_update_candidates',
        'apt_repositories', 'task', 'authcomputer', 'users', 'tables_version']:
        try:
            t = eval(table)
            t.createTable()
        except:
	    print sys.exc_type, sys.exc_value
            log.warning("Could not create table " + table + ": " + \
                str(sys.exc_type) + '- ' + str(sys.exc_value))
    hub.commit()
    hub.end()
def get_tasks(session):

    (uniq, token) = session

    if not computer.check_token(uniq, token):
        raise Exception, "Invalid authentication token"
    hub.begin()
    m = computer.select(computer.q.uniq==uniq)
    ma = list(m)
    q = len(ma)
    if q != 1:
        raise Exception, "Strange. There are more then 1 computer with uniq string =" + uniq

    client_computer = ma[0]

    log.info("Checking pending tasks for " + client_computer.hostname + \
       '(' + str(client_computer.id) + ')'  )
    remote_tasks = []
#    task._connection.debug = True
    t = task.select(task.q.computerID==client_computer.id)
    ta = list(t)
    qta = len(ta)

    if qta == 0:
        log.info("No pending tasks found for "  + client_computer.hostname + \
       '(' + str(client_computer.id) + ')' )
        return remote_tasks

    for tas in ta:
        if tas.action is None: tas.action = ''
        if tas.details is None: tas.details = ''
    log.info("Task found for "  + client_computer.hostname +  \
         '(' + str(client_computer.id) + '): ' + tas.action + ' ' + tas.details)
    remote_tasks.append((tas.action, tas.details))

    hub.commit()
    hub.end()
    return remote_tasks

def wipe_this(session, wipe_table):
    (uniq, token) = session

    if not computer.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    if wipe_table not in ['apt_current_packages', 'apt_update_candidates',
            'apt_repositories', 'task']:
	    raise Exception, "Illegal table."
	    
    hub.begin()
    conn = hub.getConnection()

    m = computer.select(computer.q.uniq==uniq)
    ma = list(m)
    q = len(ma)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " computer(s) with'" \
        + uniq + "'uniq string and it should have exactly one."

    client_computer = ma[0]

    log.info("Wiping " + wipe_table + " for "   + 
        client_computer.hostname + '(' + \
        str(client_computer.id) + ')' )
    table = eval(wipe_table)
    delquery = conn.sqlrepr(Delete(table.q, where=\
        (table.q.computerID ==  client_computer.id)))

    conn.query(delquery)
    up = update_tbl_version(wipe_table, uniq)
    hub.commit()
    hub.end()
    return up 
