#!/usr/bin/env python
# Copyright (C) 2015 McAfee, Inc.  All Rights Reserved.

from __future__ import print_function
import sys, traceback, time
import argparse
import getpass
import pprint as pp

import ratd
import ratd.api
from ratd.api import atd
import ratd.utils as utils
import ratd.cliargs
from ratd.cliargs import cliargs

import urllib3


EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# ***************************************************************************************************************************************************
# The following example of the use of the atd class is quite basic, it just connects to the atd server, uploads a file and return a value from 1-5
# indicating the potential of the file of being malware. This value can be used in third party tools where the integration with the ATD box must
# be done via API.
# ***************************************************************************************************************************************************
# In order to integrate the script with third party tools, the script returns the following values:
#    -1 ---> Error connecting to the ATD Server
#    -2 ---> Error uploading file to the ATD Server
#    -3 ---> Analysis failed
#    -4 ---> Error getting report
#    -5 ---> Error Obtaining vmprofilelist
#     0 to 5 ---> Severity level (confident of the sample to be malware
# **************************************************************************************************************************************************


def main():
    # Get the list of parameters passed from command line

    options = cliargs('sample')

    if options.password is False:
        options.password = getpass.getpass()

    if options.verbosity:
        utils.copyleftnotice()

    # Create the ATD object and connect to it

    myatd = atd(options.atd_ip, options.skipssl)
    error_control, data = myatd.connect(options.user, options.password)

    if error_control == 0:
        print (data)
        sys.exit(-1)

    if options.verbosity > 1:
        print ('Connection successful...\n')
        print ('Session Value:     ',myatd.session)
        print ('User ID:           ',myatd.userId)
        print ('ATD ver:           ',myatd.matdver)

    # Get the heartbeat value of the ATD Box
    error_control, data = myatd.heartbeat()

    if options.verbosity > 1:
        if error_control == 0:
            print ('ATD Box heartbeat: Error Obtaining value')
        else:
            print ('ATD Box heartbeat: ',data)

    # Upload file to ATD Server
    error_control, data = myatd.upload_file(options.file_to_upload, options.analyzer_profile)

    if error_control == 0:
        print (data)
        myatd.disconnect()
        sys.exit(-2)
    else:
        if options.verbosity > 2:
            print (data)

    jobId  = data['jobId']
    taskId = data['taskId']

    if options.verbosity:
        print ('\nFile %s uploaded\n'%data['file'])
        print ('jobId:    ',data['jobId'])
        print ('taskId:   ',data['taskId'])
        print ('md5:      ',data['md5'])
        print ('size:     ',data['size'])
        print ('mimeType: ',data['mimeType'])
        print ('')

    # Check status before requesting the report
    stepwait = 5
    while True:
        error_control, data = myatd.check_status(taskId)
        if error_control == 4 or error_control == 3:
            if options.verbosity:
                print ('{0} - Waiting for {1} seconds'.format(data, stepwait))
                sys.stdout.flush()
            else:
                if options.quiet is not True:
                  print ('.', end="")
                  sys.stdout.flush()
        elif error_control == -1:
            print (data)
            myatd.disconnect()
            sys.exit(-3)
        else:  # Analysis done
            if options.verbosity:
                print ('\nAnalysis done')
            break
        time.sleep(stepwait)
        if stepwait < 30:
            stepwait = stepwait + 5

    # Getting Report information
    if options.verbosity:
        print ('\nGetting report information...')

    while True:
        error_control, data = myatd.get_report(jobId)

        if error_control == 0:
            print ('\n',data)
            myatd.disconnect()
            sys.exit(-4)

        if error_control == 3:
            print ('\n',data)
            myatd.disconnect()
            sys.exit(0)

        if error_control == 1:
            try:
                severity = data['Summary']['Verdict']['Severity']
                if 'Description' in data['Summary']['Verdict']:
                    desc = data['Summary']['Verdict']['Description']
                else:
                    desc = ""
            except:
                print ('\n**BOMB parser**')
                print (data)
                myatd.disconnect()
                sys.exit(-4)
            else:
                if options.verbosity:
                    print ('\nFinal results...')
                    print (' Severity:    %s'%severity)
                    print (' Description: %s'%desc)
                    if options.verbosity > 1:
                        print (data)
                break
        # error_control = 2
        if options.verbosity:
            print (' %s - Waiting for 30 seconds...'%data)
            sys.stdout.flush()
        time.sleep(30)

    myatd.disconnect()
    sys.exit(int(severity))

if __name__ == '__main__':
    main()
