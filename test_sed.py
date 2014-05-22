#!/usr/bin/python 
import subprocess
from subprocess import Popen, PIPE
import os

outline="DANGLING /vse/alice/cern.ch/user/s/svallero/datatest/link.root -> pippo"

lines=outline.split(" ")
print lines[-3]
print lines[-2]
print lines[-1]

