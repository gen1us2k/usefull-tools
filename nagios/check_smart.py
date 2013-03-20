#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This script check Smart status of All HDDs

import subprocess
from os import popen, kill, waitpid, WNOHANG
from sys import exit
from time import sleep
from re import search
from datetime import datetime
from signal import SIGKILL
from optparse import OptionParser

errors = []
serials = []
parsed = []
controller = []
exit_status = 0

def runSmartctlWithTimeout(command):
  # Kill smartctl if timeout > 5 seconds
  start = datetime.now()
  process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  while process.poll() is None:
    sleep(0.1)
    if (datetime.now() - start).seconds > 5:
      kill(process.pid, SIGKILL)
      waitpid(-1, WNOHANG)
      return None, True
  return process.stdout.read().splitlines(), False

def getDiskList():
  return popen("ls /dev/sd?").read().splitlines()

def parseSmartctlOutput(disk):
  output, killed = runSmartctlWithTimeout("smartctl -a %s | grep -E 'Serial|Spin_Re|Start_S|Power_on|Realloc|Load_Cyc'" % disk)
  if output:
    parsed.append({disk: map(lambda x: {x.split(":")[0] : x.split(":")[1].split()[0]} if ":" in  x else {x.split()[1] : x.split()[9]}, output)})
  elif not killed:
    parsed.append({disk: "Smartctl returned not data. Probably hdd %s is dead, but block device still exist" % disk})

def checkSmartController(disk):
  output, killed = runSmartctlWithTimeout("smartctl -l error %s | grep ^ATA" % disk)
  if output:
    controller.append({disk: output[0].split(":")[1].split()[0]})

def checkValue(value, option, message):
  if int(value) > option:
    errors.append({disk: "%s is %s" %(message, value)})
    return True
  return False

if __name__ == '__main__':
  parser = OptionParser()
  parser.add_option("-r", "--reallocated", dest="realloc", default=0)
  parser.add_option("-s", "--spin-start", dest="spin_start", default=2000)
  parser.add_option("-p", "--power-on", dest="power_on", default=22000)
  parser.add_option("-o", "--spin-retry", dest="spin_retry", default=100)
  parser.add_option("-l", "--load_cycle", dest="load_cycle", default=10000)
  parser.add_option("-e", "--controller-errors", dest="cont_e", default=20)
  (options, args) = parser.parse_args()
  
  for disk in getDiskList():
    parseSmartctlOutput(disk)
    checkSmartController(disk)
  
  for diskinfo in parsed:
    for disk, output in diskinfo.iteritems():
      re = dict(zip(map(lambda x: x.keys()[0], output), map(lambda x: x.get(x.keys()[0]), output)))
      checkValue(re.get('Start_Stop_Count') or 0, options.spin_start, 'Start_Stop_Count')
      if checkValue(re.get('Reallocated_Sector_Ct') or 0, options.realloc, 'Reallocated_Sector_Ct'): exit_status = 2
      checkValue(re.get('Spin_Retry_Count') or 0, options.spin_retry, 'Spin_Retry_Count')
      if checkValue(re.get('Power_On_Hours') or 0, options.power_on, 'Power_On_Hours'): exit_status = 2
      checkValue(re.get('Load_Cycle_Count') or 0, options.load_cycle, 'Load_Cycle_Count')
      for hdd in controller:
        if hdd.keys()[0] == disk:
          if int(hdd.get(hdd.keys()[0])) > options.cont_e:
            errors.append({disk: "Controller errors count is %s" % hdd.get(hdd.keys()[0])})

  for disk in errors:
    for diskinfo in parsed:
      for hdd, output in diskinfo.iteritems():
        if disk.keys()[0] == hdd:
          out = dict(zip(map(lambda x: x.keys()[0], output), map(lambda x: x.get(x.keys()[0]), output)))
          serials.append({disk.keys()[0]: out.get('Serial Number')})

  if errors and exit_status == 2:
    print "CRITICAL: %s" % " ".join(map(lambda x: "%s %s" % (x.keys()[0], x.get(x.keys()[0])), errors))
    if serials:
      print "Broken HDD serials are %s" % " ".join(map(lambda x: "Disk %s %s" % (x.keys()[0], x.get(x.keys()[0])), serials))
    exit(exit_status)
  elif errors:
    print "WARNING: %s" % " ".join(map(lambda x: "%s %s" % (x.keys()[0], x.get(x.keys()[0])), errors))
    if serials:
      print "Broken HDD serials are %s" % " ".join(map(lambda x: "Disk %s %s" % (x.keys()[0], x.get(x.keys()[0])), serials))
    exit(1)
  else:
    print "OK - All HDD is OK"
    exit(0)
