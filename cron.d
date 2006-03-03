#
# Regular cron jobs for the nwu-agent package
#
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/1  *   * * *   nwu    /usr/bin/nwu-agent 2>&1 >> /var/log/nwuagent.log
*/1  *   * * *  root    /usr/bin/nwu-maint 2>&1 >> /var/log/nwumaint.log
