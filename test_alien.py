#!/usr/bin/python 
import subprocess
from subprocess import Popen, PIPE

# source env
command = ('source /cvmfs/alice.cern.ch/etc/login.sh && eval $( alienv printenv VO_ALICE@ROOT::v5-34-13 )')
try:
   proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
   out,err= proc.communicate()
   for outline in out.splitlines():
      print outline
   for errline in err.splitlines():
      print errline
except:
  print "Error in sourcing alien-env!"
# get token, shoud be done with passwordless certificate
# or however it is done by the stager
command = ('alien-token-init svallero')
try:
   proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
   out,err= proc.communicate()
   for outline in out.splitlines():
      print outline
   for errline in err.splitlines():
      print errline
except:
  print "Error in getting token!"

