#!/bin/bash
# all-rebuilder script.

# based on Junichi Uekawa's work:
# http://article.gmane.org/gmane.linux.debian.devel.general/48324

set -e

MIRROR=ftp.us.debian.org
ROOTCOMMAND=sudo

# kill routine
#( while sleep 1h; do killall linux; done ) & 

SUCCESS=nwu-success
FAIL=nwu-fail
WORKING=nwu-work
mkdir $SUCCESS || true
mkdir $FAIL || true
mkdir $WORKING || true

if [ ! -f release.sh ]; then
    echo "You must be in the NWU svn repository root dir"
    exit 1
fi

function call() {
    component=$1
    temp=$2
    local LOGFILE=${WORKING}/"$PROGNAME.log"

    echo "Testing $1 process"
    #if pbuilder execute --bindmounts "$temp" --logfile "$LOGFILE" trunk/install-tests/pbuilder-$1.sh "$temp"; then
    if pbuilder execute --bindmounts "$temp" trunk/install-tests/pbuilder-$1.sh "$temp"; then
    mv "$LOGFILE" "$SUCCESS"
    echo "  $1 successful"
    else
    mv "$LOGFILE" "$FAIL"
    echo "  $1 fail"
    fi
}

#$ROOTCOMMAND  apt-get update

tempfile=/tmp/nwu$$
sh release.sh nwu ${tempfile}
cd ${tempfile}/nwu
pdebuild --buildresult ./ 
cp /etc/nwu/server.pem ./
dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz
dpkg-scansources . /dev/null | gzip -9c > Sources.gz
cd -
#$ROOTCOMMAND pbuilder update 
pbuilder update 

TESTS="server-install"

for A in $TESTS; do 
    #waitingroutine
    call $A ${tempfile}
    exit
done

rm -rf ${tempfile}
