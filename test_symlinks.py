#!/usr/bin/python 
import subprocess
from subprocess import Popen, PIPE

watched_dir="/vse"

command = ('symlinks -r '+watched_dir+'')
try:
   proc = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
   out,err= proc.communicate()
   for outline in out.splitlines():
      if 'dangling' in outline:
         # questo proprio solo per puntiglio...
         outline = outline.replace('dangling:','DANGLING')
         print outline
except:
  print "Error in running Linux symlinks!"
