#!/bin/bash

#
# af-mirror-verify.sh -- by Sara Vallero <svallero@to.infn.it>
#
# This script makes a third replica of a file using alien_mirror
# and verifies the integrity of the zip archive and the main .root file.
#
# afdsmgrd variables are ignored: /etc/aafrc variables are used instead.
#

# Source automatic AliEn stuff
source /home/vseadmin/afdsmgrd/etc/vserc || exit 1 # CHANGE!

# Source environment for xrddm and ROOT (AliEn is included)

source /cvmfs/alice.cern.ch/etc/login.sh
eval $( alienv printenv VO_ALICE@ROOT::v5-34-13 )

# Exit on error
function Abort() {
  echo "FAIL $Url Reason: $1"
  exit 1
}

# Remove file and empty parents
function DeepRm() {
  local CurDir
  rm -f "$1"
  CurDir=$(dirname "$1")
  while [ "$CurDir" != "/" ]; do
    rmdir "$CurDir" || break
    echo $CurDir
    CurDir=$(dirname "$CurDir")
  done
}

#
# Entry point
#

export Url="$1"
Tree="$2"

PosixPath=${Url%%#*}
Anchor=${Url##*#}
[ "$Anchor" == "$Url" ] && Anchor=''

# They both work. The first one also resolves '.' and '..'
#PosixPath=$(readlink -m "$PosixPath")
PosixPath=$(echo "/$PosixPath" | sed 's#//*#/#g')

# Always (re)download by default
Download=1

#if [ -e "$PosixPath" ] ; then
#
#  # File already there, but it might be a partially downloaded zip that xrddm
#  # has not had the chance to check yet! So, check for zip integrity here
#  Ext=${PosixPath##*.}
#  [ "$Ext" == "$PosixPath" ] && Ext=''
#  Ext=$(echo "$Ext" | tr '[:upper:]' '[:lower:]')
#
#  if [ "$Ext" == 'zip' ]; then
#    # Exit code for zip -T failure is 8
#    zip -T "$PosixPath" && Download=0 || DeepRm "$PosixPath"
#  else
#    # File is not a zipfile: do not re-download it
#    Download=0
#  fi
#
#fi

# Always force re-download
[ -e "$PosixPath" ] && rm -f "$PosixPath"

# Download file if told so
if [ "$Download" == 1 ]; then

  # Alien path
  AlienPath=${PosixPath:${#VSE_SHARED_DATA}}
  MirrorPath=$AlienPath
  AlienPath="alien://$AlienPath"

  # Uncomment for debug
  #echo "Url       => $Url"
  #echo "PosixPath => $PosixPath"
  #echo "Anchor    => $Anchor"
  #echo "Tree      => $Tree"
  #echo "AlienPath => $AlienPath"
  #echo "Command   => xrddm -a $AlienPath $PosixPath ..."

  # Create destination directory structure
  mkdir -p $(dirname "$PosixPath") || Abort 'mkdir'

  # Get token
  alien-token-init $VSE_USER || Abort 'alien-token-init'

  # Make an additional replica using alien_mirror
  alien_mirror -w $MirrorPath $VSE_SE
  if [ $? != 0 ]; then
    DeepRm "$PosixPath"
    Abort 'alien_mirror' 
  fi
  #chmod 0644 "$PosixPath"

  # Get PFN of mirrored file
  pfn=`alien_whereis $MirrorPath | grep $VSE_SE`
  if [ $? != 0 ]; then
    DeepRm "$PosixPath"
    Abort 'alien_whereis' 
  fi
  # Posix  file name
  pfn=`echo $pfn | sed 's/SE.*\/\///g'`
  pfn="$VSE_SE_POSIX_BASE/$pfn"
  #echo "MirrorPath: $MirrorPath" >> /tmp/tmp.log
  #echo "PosixPath: $PosixPath" >> /tmp/tmp.log
  #echo "PFN: $pfn" >> /tmp/tmp.log
  # Create link to file location on SE
  ln -s $pfn $PosixPath
  #echo `ls -l $PosixPath` >> /tmp/tmp.log
  if [ $? != 0 ]; then
    DeepRm "$PosixPath"
    Abort 'ln -s' 
  fi
fi

# Choose proper verification macro (standard ROOT or custom afdsmgrd)
#if [ "$VSE_CUSTOM_AFDSMGRD" == '' ]; then
VerifyMacro="$ROOTSYS/etc/proof/afdsmgrd-macros/Verify.C"
#else
#  VerifyMacro="$VSE_CUSTOM_AFDSMGRD/libexec/afdsmgrd-macros/Verify.C"
#fi

# Now, re-assemble the anchor and check the file with ROOT; ROOT history is off
TempOut=$(mktemp /tmp/af-mirror-verify-root.XXXXX)
export ROOT_HIST=0
root.exe -b -q \
  "$VerifyMacro"'("file://'$PosixPath\#$Anchor'", "'$Tree'")' 2>&1 | tee -a $TempOut

# Decide whether to remove the file or not: if integrity check fails, file
# should be removed to save space
grep '^OK ' $TempOut > /dev/null || DeepRm "$PosixPath"

# Remove output file
rm -f $TempOut
