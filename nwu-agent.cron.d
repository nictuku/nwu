#
# Regular cron jobs for the nwu-agent package
#
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root

0,10,20,30,40,50  *   * * *   nwuagent    /usr/bin/nwu-agent > /dev/null 2>&1
5,15,25,35,45,55  *   * * *  root    /usr/sbin/nwu-maint > /dev/null 2>&1
