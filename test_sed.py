#!/usr/bin/python 
import subprocess
from subprocess import Popen, PIPE
import os

outline="		 SE => ALICE::Torino::SE  pfn =>root://alice-xrd.to.infn.it:1094//09/43427/a35d75fe-e02e-11e3-bde3-9bcb3904c079"

lines=outline.split("/")
print lines[-3]
print lines[-2]
print lines[-1]

pfn="/glfs/alice-xrd/xrootd/09/43427/a35d75fe-e02e-11e3-bde3-9bcb3904c079"
lfn="/alice/cern.ch/user/s/svallero/datatest/AliAOD.root"
os.symlink(pfn,lfn)
