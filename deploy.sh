#!/bin/bash
# Run on local machine

set -e

reponame="https://github.com/thiscoldhouse/zoebee2.0.git"
localdeploy="zoebee.fun"
server="zoebee.fun"

cd /tmp
git clone $reponame $localdeploy
cd zoebee.fun
thiscommit=$(git rev-parse HEAD)
deploytime=$(date +%s)
deployname="$thiscommit-$deploytime"
cd ..
tar -czvf $deployname.tar.gz zoebee.fun/

echo "Sending code to the servers"
echo "First, removing old code"
ssh -t aleruiz@$server "rm -rf /usr/src/zoebee.fun/* "
echo "Sending new code"
scp /tmp/$deployname.tar.gz aleruiz@$server:/tmp/

# note add:
# /usr/src/venv/zoebee.fun/bin/pip install -r /usr/src/zoebee.fun/requirements.txt &&
# before the restart. requirements are currently broken.
ssh -t aleruiz@$server "
    tar -xf /tmp/$deployname.tar.gz -C /usr/src/deploys/ &&
    mv /usr/src/deploys/zoebee.fun /usr/src/deploys/$deployname &&
    sudo /bin/rm -rf /usr/src/zoebee.fun &&
    sudo /bin/ln -s /usr/src/deploys/$deployname /usr/src/zoebee.fun &&
    sudo service zoebee.fun restart &&
    sudo service zoebee.fun status"

echo "Cleaning up"
rm -rf $localdeploy
rm -rf $deployname.tar.gz
echo "Done"
