#
# Regular cron jobs for the nwu-agent package
#
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root

10-50/10  *   * * *   nwuagent    /usr/bin/nwu-agent > /dev/null 2>&1
5-55/10  *   * * *  root    /usr/sbin/nwu-maint > /dev/null 2>&1
