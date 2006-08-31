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

NO_START=0

. /etc/default/nwu-server

case "$1" in
  start)
    log_begin_msg "Starting Network Wide Updates Server"
    
    if [ "$NO_START" -eq 1 ]; then
          log_end_msg 1
	  echo "   !! Will not start."
	  echo "      See /etc/default/nwu-server"
	  exit
    fi


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
        echo
        if [ "$?" -eq 0 ]; then
            log_end_msg 0
        else
            log_end_msg 1
        fi
    fi
  ;;
  stop)
    log_begin_msg "Stopping Network Wide Updates Server"
    if [ -f "$PIDFILE" ];
       then PID=`cat ${PIDFILE}`;
    fi
    if [ ! -z ${PID} ] && [ -d /proc/${PID} ]; then
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
