#!/bin/bash
# pbuilder example script.
# Copyright 2003 Junichi Uekawa
#Distributed under GPL version 2 or later

# Adapted by Yves Junqueira
# Copyright 2006 Yves Junqueira

# This will install a package using APT and see if that fails.
DEBPAKS="$1/nwu"

if [ ! -d "$DEBPAKS" ];then
echo "Directory not found: $DEBPAKS"
fi

set -ex

INSTALLTESTPID=$$
( sleep 1h ; kill $INSTALLTESTPID ) &
KILLPID=$!
echo "deb http://archive.ubuntu.com/ubuntu edgy universe" >> /etc/apt/sources.list
echo "deb file:$DEBPAKS ./" >> /etc/apt/sources.list
apt-get update
apt-get install -y --force-yes nwu-server
sed -e 's/NO_START.*/NO_START=0/g' -i /etc/default/nwu-server
cp $DEBPAKS/server.pem /etc/nwu/server.pem
chown nwuserver.nwuserver /etc/nwu/server.pem
chmod 660 /etc/nwu/server.pem
/etc/init.d/sysklogd start
nwu-server -i
/etc/init.d/nwu-server start
apt-get install --force-yes --yes nwu-agent < /dev/null
sed -e 's/server_uri.*/server_uri = https:\/\/nictuku.dyndns.org:8088/g' -i /etc/nwu/agent.conf
sudo -u nwuagent nwu-agent
nwu list|grep -q $(hostname) || ( echo "hmm something went wrong. $(hostname) was not found in the list" ; exit 1)
nwu view 1 packages
kill $KILLPID

# known bugs according to Christian Perrier.

# anacron 	MQ	134017
# Base-passwd	CP	184979
		
# exim		86210
# Kernel-package		115884
# Sendmail	CP	?
# wvdial	CP	219151
		
# Nessusd	CP	191925
# Libssl0.9.7		?
		
# php4		122353
# seyon		147269



