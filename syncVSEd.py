#!/usr/bin/python

###############################################################################
#                                                                             #
# Daemon to check VSE consistency with storage.                               #
#                                                                             #
# In the main loop we do:                                                     #
#   1) use Inotify to detect changes in monitored dir (/vse).                 #
#      We check for create/destroy links. If a link is removed,               #
#      but the target file is still in the local SE -> relink                 #
#   2) use Symlinks to detect dangling links. If the link target              #
#      was removed form the AliEN catalogue, remove link.                     # 
# In all other inconsistency cases, returns an error.                         # 
#                                                                             #
# Based on python module "daemon", which implements the well-behaved          #
# daemon specification of PEP3143.                                            # 
#                                                                             #
# To kick off the script, run the following from the python directory:        #
# python syncVSE.py start                                                     # 
#                                                                             #
# TODO init script                                                            #
#                                                                             #
# Mailto: svallero@to.infn.it                                                 #
#                                                                             #
###############################################################################

# Configuration goes here ##################################################### 
logfile="/tmp/syncVSEd.log"
pidfile="/tmp/syncVSEd.pid"
# time given to notifier to read events
inotify_timeout=10
# sleep time for main loop
sleep_time=10 
watched_dir="/vse"
local_se="ALICE::Torino::SE"
alien_user="svallero"
se_posix_path="/glfs/alice-xrd/xrootd"
###############################################################################

# Standard python libs
import logging
import time
import sys
import os
import subprocess
from subprocess import Popen, PIPE

# Third party libs
from daemon import runner
import pyinotify

# Logger ----------------------------------------------------------------------
logger = logging.getLogger("syncVSEdLog")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
lhandler = logging.FileHandler(logfile)
lhandler.setFormatter(formatter)
logger.addHandler(lhandler)

# Daemon class, main loop is defined here -------------------------------------
class App():
    
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  pidfile
        self.pidfile_timeout = 5
            
    def run(self):
        logger.info("********************************")
        logger.info("*** Starting daemon syncVSEd ***")
        logger.info("********************************")
        # source AliEn environment (CVMFS style)
        command = ('source /cvmfs/alice.cern.ch/etc/login.sh && eval $( alienv printenv VO_ALICE@ROOT::v5-34-13 )')
        run_shell_cmd(command)
	# Inotify stuff: 
	# watch manager
	wm = pyinotify.WatchManager()
	# watched events
	mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE
	# event handler
	ihandler = EventHandler()
	# notifier
	notifier = pyinotify.Notifier(wm,ihandler,timeout=inotify_timeout)
	# add dir to watch recursively
	wm.add_watch(watched_dir, mask, rec=True)
         
        # MAIN LOOP
        while True:
            # Check CREATE/DELETE links
            logger.info('Inotify check ('+str(inotify_timeout)+'s timeout)...')
            inotify_check(notifier)
            # Check DANGLING links
            logger.info("Symlinks check...")
            symlinks_check()  
            # Sleep   
            logger.info('Sleeping '+str(sleep_time)+'s...')
            time.sleep(sleep_time)

# Inotify stuff ---------------------------------------------------------------
class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        logger.warn('CREATED:'+event.pathname+'')

    def process_IN_DELETE(self, event):
        path=event.pathname
        logger.warn('REMOVED:'+path+'')
        # check if file is still in the SE
        logger.info("Checking if file is still in local SE...") 
        lfn = path.replace(watched_dir,"")
        target=query_catalog(lfn)
        if "NULL" not in target:
           # if yes re-link 
           logger.info("Re-linking file...")
           target_split=target.split("/") 
           pfn=''+se_posix_path+'/'+target_split[-3]+'/'+target_split[-2]+'/'+target_split[-1]+''
           try:
              os.symlink(pfn,path);
           except:
              logger.error("Failed to re-link!")
        else: 
           logger.info("File not found! Doing nothing.")


def inotify_check(notifier):
    assert notifier._timeout is not None, 'Notifier must be constructed with a short timeout!'
    notifier.process_events()
    #loop in case more events appear while we are processing
    while notifier.check_events():
       notifier.read_events()
       notifier.process_events()

# Symlinks stuff --------------------------------------------------------------
def symlinks_check():
    # here we use the Linux utility "symlinks"
    command = ('symlinks -r '+watched_dir+'')
    try:
       proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True) 
       out,err= proc.communicate()
       for outline in out.splitlines():
          if 'dangling' in outline: 
             # questo proprio solo per puntiglio...
             outline=outline.replace('dangling:','DANGLING')
             logger.warn(outline) 
             logger.info("Check if target is still in catalogue...")
             outline_split=outline.split(" ")
             path=outline_split[-3]  
             lfn = path.replace(watched_dir,"")
             target=query_catalog(lfn)
             if "NULL" in target:
                logger.info("Target not in catalogue. Removing link...")
                try:
                   os.remove(path)
                except:
                   logger.error("Could not remove link!")    
             else:
                logger.error("Target not in local SE, but still in catalogue!") 
    except:
       logger.error("Error in running Linux symlinks!")

# Query catalog ---------------------------------------------------------------
def query_catalog(lfn):
    # function to check if given file is supposed to be in the local SE
    retval="NULL"
    # check if there is a valid token
    logger.debug("Check for valid token...")
    command = ('alien-token-info '+alien_user+'')
    proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    out,err= proc.communicate()
    valid=False
    for outline in out.splitlines():       
       if 'Token is still valid!' in outline:
          valid=True 
    if not valid:
       logger.info("No valid token found, requesting a new one...")
       # get token, shoud be done with passwordless certificate
       command = ('alien-token-init '+alien_user+'')
       run_shell_cmd(command)
    # query the AliEn catalogue
    logger.info("Querying the AliEn catalogue...") 
    command = ('alien_whereis '+lfn+'') 
    proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    out,err= proc.communicate()
    for outline in out.splitlines():       
      if local_se in outline:
         logger.info(outline)
         retval = outline 

    return retval

# Safely run a shell command --------------------------------------------------
def run_shell_cmd(command):
   try:
      proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
      out,err= proc.communicate()
      for outline in out.splitlines():
         logger.debug(outline)
      for errline in err.splitlines():
         logger.debug(errline)
   except:
      logger.error('Running command '+command+'')
  
# Define daemon runner --------------------------------------------------------
app = App()
daemon_runner = runner.DaemonRunner(app)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[lhandler.stream]
# Run daemon
daemon_runner.do_action()

