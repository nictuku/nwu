#
# Regular cron jobs for the nwu-agent package
#
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root
*/10  *   * * *   nwuagent    /usr/bin/nwu-agent > /dev/null 2>&1
*/5  *   * * *  root    /usr/sbin/nwu-maint > /dev/null 2>&1
