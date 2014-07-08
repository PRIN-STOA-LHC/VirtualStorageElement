#!/bin/bash

source /cvmfs/alice.cern.ch/etc/login.sh
eval $( alienv printenv VO_ALICE@ROOT::v5-34-13 )
 
CONFIG_FILE="/home/vseadmin/afdsmgrd/config/afdsmgrd.conf"
PID_FILE="/home/vseadmin/afdsmgrd/run/afdsmgrd.pid"
DEBUG_LEVEL="high"
LOG_FILE="/home/vseadmin/afdsmgrd/log/afdsmgrd.log"
LIBEXEC_PATH="$ROOTSYS/etc/proof"
# echo $LIBEXEC_PATH
afdsmgrd -c $CONFIG_FILE -p $PID_FILE -d $DEBUG_LEVEL -l $LOG_FILE -e $LIBEXEC_PATH &

