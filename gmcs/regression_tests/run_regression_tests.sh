#!/bin/bash

# Script for running all existing matrix regression tests.
# Be sure that $CUSTOMIZATIONROOT is set appropriately
# (i.e., to point to the matrix/gmcs directory you
# intend to test... the regression_tests directory with that
# gmcs/directory is the one that will be active).
# Much copied from logon/parse.

unset DISPLAY
unset LUI

###
### INITIALIZATION CHECKS
###

if [ -z "${LOGONROOT}" ]; then
  echo "run-regression-tests: unable to determine \$LOGONROOT directory; exit."
  exit 1
fi

if [ -z "${CUSTOMIZATIONROOT}" ]; then
  echo "run-regression-tests: unable to determine \$CUSTOMIZATIONROOT directory; exit."
  exit 1
fi

# set the appropriate Python version
python_cmd='python'
if ! echo $( $python_cmd -V 2>&1 ) | grep -q "Python 2\.[5,6,7]"; then
  echo "Default Python version incompatible. Attempting to find another..." >&2
  if which python2.5 >/dev/null; then
    python_cmd='python2.5'
  elif which python2.6 >/dev/null; then
    python_cmd='python2.6'
  elif which python2.7 >/dev/null; then
    python_cmd='python2.7'
  else
    echo "No compatible Python version found. Exiting."
    exit 1
  fi
  echo "  Found $( $python_cmd -V 2>&1 ). Continuing." >&2
fi

###
### COMMON VARIABLES AND SETTINGS
###

#
# include a shared set of shell functions and global parameters, including the
# architecture identifier .LOGONOS.
#
. ${LOGONROOT}/etc/library.bash
date=$(date "+%Y-%m-%d")
datetime=$(date)
count=1
limit=1000
best=1000

# Parameters which are the same for all regression test:
rtestdir="${CUSTOMIZATIONROOT}/regression_tests/"
skeletons="$rtestdir/skeletons/"
choices="$rtestdir/choices/"
grammars="$rtestdir/grammars"
tsdbhome="$rtestdir/home/"
logs="$rtestdir/logs/"

### LOG FILES

# Main log file to look at tsdb output.
TSDBLOG="$logs/tsdb.${date}.log"
if [ -e ${TSDBLOG} ]; then
    rm ${TSDBLOG}
fi

# Create one log file with results from all tests, appending on 
# comments.
# 2008-08-22: By request not overwriting the log file
# but appending instead, with time stamps.
masterlog="$logs/regression-tests.$date"
echo "============ $datetime ============" >> $masterlog

###
### TEST PREPARATION
###

# Get the list of regression tests from the regression-test-index:
# or from command-line input.
if [ -z $1 ]; then
    lgnames=`$python_cmd ${CUSTOMIZATIONROOT}/regression_tests/regressiontestindex.py --lg-names`
    if [ $? != 0 ]; then
    echo "run-regression-tests: Problem with regression-test-index, cannot run regression tests."
    exit 1
    fi
else 
    lgnames=$1
fi

# Clear any existing regression test files that can cause conflicts
for lgname in $lgnames
do
    rm -rf $grammars/$lgname
    rm -f $logs/$lgname.$date
    rm -rf $tsdbhome/current/$lgname
done

# Create fresh copy of matrix-core
rm -rf ${CUSTOMIZATIONROOT}/matrix-core
pushd ${CUSTOMIZATIONROOT}/.. >/dev/null
./install -c ${CUSTOMIZATIONROOT}/matrix-core >/dev/null
popd >/dev/null

###
### TSDB GOLD STANDARD COMPARISONS
###

# Now do essentially the same things as one-regression-test for each one:

for lgname in $lgnames
do 
    printf "%-70s " "$lgname..."

    # Set skeleton, grammar, gold-standard for comparison, and
    # target directory.
    skeleton="$skeletons/$lgname"
    gold="gold/$lgname"
    choicesfile="$choices/$lgname"
    grammardir="$grammars/$lgname"
    target="current/$lgname"
    log="$logs/$lgname.$date"

    # Validate
    $python_cmd ${CUSTOMIZATIONROOT}/../matrix.py v $choicesfile >> $log
    if [ $? != 0 ]; then
      echo "INVALID!"
      echo "$lgname choices file did not pass validation." >> $log
      continue
    fi
    # Customize
    $python_cmd ${CUSTOMIZATIONROOT}/../matrix.py cf $choicesfile $grammardir >> $log
    if [ $? != 0 ]; then
      echo "FAIL!"
      echo "There was an error during the customization of the grammar." >> $log
      continue
    fi

    subdir=`ls -d $grammardir/*/`
    grammar=$subdir/lkb/script
    grm_file=`ls $subdir/*-pet.grm`
    #mkdir -p $tsdbhome/$target
    #cut -d@ -f7 $skeleton/item | cheap -mrs -tsdbdump $tsdbhome/$target $grm_file 2>${TSDBLOG} >${TSDBLOG}
    # cheap makes a bad item file, so just copy over the original one
    #cp $skeleton/item $tsdbhome/$target/item

    #if [ $status = 17 ]; then
    #echo "run-regression-tests: call-customize failed for $lgname... continuining with other regression tests."
    #echo "call-customize failed because old grammar was in the way." >> $log
    #elif [ $status = 18 ]; then
    #echo "run-regression-tests: call-customize failed for $lgname... continuining with other regression tests."
    #echo "no choices file at path regression_tests/choices/$lgname." >> $log
    #elif [ $status != 0 ]; then

    #    echo "run-regression-tests: customization failed for $lgname... continuing with other regression tests."; 
    #    echo "Customization failed; no grammar created." >> $log

    #else

    # Set up a bunch of lisp commands then pipe them to logon/[incr tsdb()]
    
    # I don't see how the following can possibly do anything,
    # since nothing has yet invoked [incr tsdb()] or lisp.
    # But let's give it a try anyway...
      # Have to calculate after the grammar is created since the directory is
      #no longer always named "matrix")
    {
        options=":error :exit :wait 300"

        echo "(setf (system:getenv \"DISPLAY\") nil)"

        # Use the following for PET parsing
        #echo "(setf *tsdb-cache-connections-p* t)"
        #echo "(setf *pvm-encoding* :utf-8)"
        #echo "(setf *pvm-cpus* (list (make-cpu"
        #echo "  :host (short-site-name)"
        #echo "  :spawn \"${LOGONROOT}/bin/cheap\""
        #echo "  :options (list \"-tsdb\" \"-packing\" \"-mrs\" \"$grm_file\")"
        #echo "  :class :$lgname :name \"$lgname\""
        #echo "  :grammar \"$lgname (current)\""
        #echo "  :encoding :utf-8"
        #echo "  :task '(:parse) :wait 300 :quantum 180)))"
        #echo "(tsdb:tsdb :cpu :$lgname :task :parse :file t)"

        # Use the following for LKB parsing
        echo "(lkb::read-script-file-aux \"$grammar\")"

        echo "(setf tsdb::*process-suppress-duplicates* nil)"
        echo "(setf tsdb::*process-raw-print-trace-p* t)"

        echo "(setf tsdb::*tsdb-home* \"$tsdbhome\")"
        echo "(tsdb:tsdb :skeletons \"$skeletons\")"

        echo "(setf target \"$target\")"
        echo "(tsdb:tsdb :create target :skeleton \"$lgname\")"

        echo "(tsdb:tsdb :process target)"

        echo "(tsdb::compare-in-detail \"$target\" \"$gold\" :format :ascii :compare '(:readings :mrs) :append \"$log\")"

    } | ${LOGONROOT}/bin/logon \
        -I base -locale no_NO.UTF-8 -qq 2> ${TSDBLOG} > ${TSDBLOG}
# ${source} ${cat} 
# FIXME: There is probably a more appropriate set of options to
# send to logon, but it seems to work fine as is for now. 

    #rm -rf $grammardir

# When the grammar fails to load, [incr tsdb()] is not creating
# the directory.  So use existence of $tsdbhome/$target to check
# for grammar load problems.

    if [ ! -e $tsdbhome/$target ]; then
        echo "ERROR!"
        echo "Probable tdl error; grammar failed to load." >> $log
    elif [ -s $log ]; then
        echo "DIFFS!"
    else
        echo "Success!"
    fi
done

# Check through tsdb log file for any errors, and report
# whether the results can be considered valid.

for lgname in $lgnames
do
    log="$logs/$lgname.$date"
    echo -ne "$lgname" >> $masterlog
    if [ -s $log ]; then
        echo -ne ": " >> $masterlog
        $python_cmd ${CUSTOMIZATIONROOT}/regression_tests/regressiontestindex.py --comment $lgname | cat >> $masterlog
        echo "" >> $masterlog
        cat $log >> $masterlog
        echo "" >> $masterlog
    else
        echo "... Success!" >> $masterlog
    fi
done

# Notify user of results:

echo "Grepping for 'error' in tsdb log:"
echo ""

grep -i "error" ${TSDBLOG}

echo ""
echo "Results of the regression tests can be seen in"
echo "$masterlog"
