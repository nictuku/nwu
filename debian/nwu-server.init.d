#
# InitScript for NWU Server
#

#!/bin/sh

NWUSERVER="/usr/sbin/nwu-server"
CONFIG="/etc/nwu/server.conf"
SSLCERT="/etc/nwu/server.pem"
PIDFILE="/var/run/nwu-server/nwu-server.pid"

# Carregando funções lsb
. /lib/lsb/init-functions

case "$1" in
  start)
    log_begin_msg "Starting Network Wide Updates Server"
    if [ ! -f ${CONFIG} ]; then
	log_end_msg 1
	echo "   !! No config file (${CONFIG}) fonud."
        echo "      Please take a look at /usr/share/doc/nwu-server/README"
	echo "      Example available at /usr/share/doc/nwu-server/example/"
    elif [ ! -f ${SSLCERT} ]; then
	log_end_msg 1
	echo "   !! No SSL Certificate (${SSLCERT}) found."
        echo "      Instructions for creating a certificate at /usr/share/doc/nwu-server/README"
    else
	${NWUSERVER}
	log_end_msg 0
    fi
  ;;
  stop)
    log_begin_msg "Stopping Network Wide Updates Server"
    PID=`cat ${PIDFILE}`
    if [ ${PID} != "" ] && [ -d /proc/${PID} ]; then
	kill ${PID}
	log_end_msg 0
    else
	log_end_msg 1
    fi
  ;;
  restart)
    $0 stop
    $0 start
    ;;
  *)
        log_success_msg "Usage: $0 {start|stop|restart}"
        exit 1
  ;;
esac 

exit 0
