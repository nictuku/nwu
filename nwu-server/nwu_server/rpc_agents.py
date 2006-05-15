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
import auth
hub = PackageHub()
__connection__ = hub

def create_tables():
    """Creates required tables in the database.
    """
    hub.begin()
    log.debug("Creating necessary tables in the database.")

    for table in ['computer', 'apt_current_packages', 'apt_update_candidates',
        'apt_repositories', 'task', 'authcomputer', 'users']:
        try:
            t = eval(table)
            t.createTable()
        except:
            log.warning("Could not create table " + table + ": " + \
                str(sys.exc_type) + ' ' + str(sys.exc_value))
    hub.commit()
    hub.end()
 
def add_computer(password, uniq, hostname, os_name, os_version):
    """Adds the given computer to the computers database.
    """
    hub.begin()
    log.info("Creating computer " + uniq + " " + hostname + " " +\
         os_name + " " + os_version)
    m = computer(uniq=uniq,hostname=hostname, os_name=os_name,
        os_version=os_version,password=password)

    hub.commit()
    hub.end()
    return True

def get_tasks(session):

    (uniq, token) = session

    if not auth.check_token(uniq, token):
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

def wipe_tasks(session):
    (uniq, token) = session

    if not auth.check_token(uniq, token):
        raise Exception, "Invalid authentication token"

    hub.begin()
    m = computer.select(computer.q.uniq==uniq)
    ma = list(m)
    q = len(ma)
    if q != 1:
        raise Exception, "Strange. There are " +  q +  " computer(s) with'" \
        + uniq + "'uniq string and it should have exactly one."

    client_computer = ma[0]

    log.info("Wiping tasks for "   + client_computer.hostname + '(' + \
        str(client_computer.id) + ')' )


    delquery = conn.sqlrepr(Delete(task.q, where=\
        (task.q.computerID ==  client_computer.id)))

    conn.query(delquery)

    hub.commit()
    hub.end()
    return True

def session_setup(uniq, token):
    """Setups the session for agent-aggregator or agent-manager communication.

    The token string comes from the authentication process.

    Returns session object to be used by the agent in later
    communcation steps.
    """
    hub.begin()
    log.info("Setting session for computer " + uniq + ".")

    # FIXME: test if token is valid here.
    query_check_m = computer.select(computer.q.uniq==uniq)
    check_m = list(query_check_m)

    password = ''

    hub.commit()
    hub.end()
    if len(check_m) == 0:
        return False

    if auth.check_token(uniq, token):
        return uniq, token

    # FIXME: return False or raise an exception?
    raise Exception, "Wrong token for " + uniq

