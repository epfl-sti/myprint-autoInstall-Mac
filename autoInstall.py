#!/usr/bin/env python

from __future__ import print_function
__author__ = 'jaep'

import platform
import urllib2
import os
from subprocess import Popen, PIPE
import hashlib
import re
import shutil
import sys
import locale

def get_os_name():
    return platform.system()

def Check_OS():
    print("Checking OS...", end='')
    if get_os_name() == "Darwin":
        print("Done")
    else:
        print("Failed.")
        print("This script is only intended for mac os only")
        exit()

def getlanguage():
    try:
        return locale.getdefaultlocale()[0].split('_')[0]
    except:
        return 'en'

def ShouldStoreCredentials():
    answer = ''
    p = re.compile('^([YN])$', re.IGNORECASE)
    while (p.match(answer) == None):
        answer = raw_input('Do you want to store your credentials into keychain [Y/N]?')
    if p.match(answer).group().lower() == 'n':
        return False
    else:
        return True

def LaunchProcess(CommandToLaunch):
    proc = Popen(CommandToLaunch, shell=True, stdout=PIPE, stderr=PIPE)
    return proc.communicate()[0].decode('utf-8')

def Enable_DEBUG_on_CUPS():
    print("Turning on DEBUG output on CUPS...", end="")
    cmd = "cupsctl --debug-logging"
    process_output = LaunchProcess(cmd)
    if process_output == "":
        print("Done.")
    else:
        print("Failed.")
        print(process_output)

def Disable_DEBUG_on_CUPS():
    print("Turning on DEBUG output on CUPS...", end="")
    cmd = "cupsctl --no-debug-logging"
    process_output = LaunchProcess(cmd)
    if process_output == "":
        print("Done.")
    else:
        print("Failed.")
        print(process_output)

def Stop_CUPS():
    print("Stopping CUPS...", end="")
    cmd = "launchctl stop org.cups.cupsd"
    process_output = LaunchProcess(cmd)
    if (process_output == ""):
        print("Done.")
    else:
        print("Failed.")
        print(process_output)

def Start_CUPS():
    print("Starting CUPS...", end="")
    cmd = "launchctl start org.cups.cupsd"
    process_output = LaunchProcess(cmd)
    if (process_output == ""):
        print("Done.")
    else:
        print("Failed.")
        print(process_output)

def Check_Previous_Installation():
    print("Checking if the printer is already installed...", end="")
    cmd = "lpstat -p | grep POOL1"
    printer_list_result = LaunchProcess(cmd)
    if printer_list_result != "":
        print("Done")

        print("Removing already installed printer...", end="")
        cmd = "lpadmin -x POOL1"
        printer_removal_result = LaunchProcess(cmd)
        if printer_removal_result == "":
            print("Done")
        else:
            print("Error. The message was: " + printer_removal_result)
    else:
        print("Done")

def Install_Printer():
    print("Installing the printer locally...", end='')
    cmd = 'lpadmin -p POOL1 -E -v smb://print1.epfl.ch/pool1 -P /tmp/POOL1.ppd -o printer-is-shared=false -o PageSize=A4 -u allow:all -o auth-info-required=username,password -o XRBannerSheet=None -o printer-make-and-model="Xerox WorkCentre 7665, 3.5.1";'
    printer_install_result = LaunchProcess(cmd)
    if len(printer_install_result) == 0:
        print("Done")
    else:
        print("Failed.")
        print("The error message was: " + printer_install_result)
        exit()

def Submit_Dummy_Job():
    print("Submitting a sample print job...", end='')
    cmd = "lpr /usr/share/cups/data/testprint"
    dummyJobSubmission = LaunchProcess(cmd)
    if dummyJobSubmission == '':
        print("Done.")
    else:
        print("Failed.")
        print(dummyJobSubmission)

def Retract_Dummy_Job():
    print("Retracting the sample print job...", end='')
    cmd = "lprm POOL1"
    dummyJobDeletetion = LaunchProcess(cmd)
    if dummyJobDeletetion == '':
        print("Done.")
    else:
        print("Failed.")
        print(dummyJobDeletetion)

def Store_Credentials():
    import getpass

    # Get user's credentials to store into the KeyChain
    username = raw_input('Please type your username:')
    password = getpass.getpass('Please type your password:')

    # Delete the already existing entry into the Keychain
    deletionResult = LaunchProcess("security delete-internet-password -l POOL1")
    if deletionResult != '':
        print("The existing entry in the Keychain was removed.")
    else:
        print("There was no pre-existing entry in the Keychain")

    # Add the set of credentials into the Keychain
    cmd = "security add-internet-password -a " + repr(username) + " -l 'POOL1' -r 'smb ' -s 'print1.epfl.ch' -w " + repr(password) + " -T '/System/Library/CoreServices/NetAuthAgent.app/';"
    addResult = LaunchProcess(cmd)
    if addResult != '':
        print('An error occurred. the message was: ' + addResult)
    else:
        print('Credentials successfully added to Keychain.')

print('*'*80)
print('myPrint driver automated installation')
print('*'*80)
print('Running Python version ' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2]))

# Check if the script is launched from a Mac or another OS.
Check_OS()

fileName = "POOL1.ppd"
tempPath = "/tmp"
AmazonBasePath = "https://s3-eu-west-1.amazonaws.com/uctools/"

FileFullPath = os.path.join(tempPath, fileName)
FileURL = AmazonBasePath + urllib2.quote(fileName)

# Check if the driver image is already present on disk and download it if necessary
if not os.path.isfile(FileFullPath):

    # Download the driver from server
    print("Downloading driver image from server...", end='')
    with open(FileFullPath, 'wb') as f:
        f.write(urllib2.urlopen(FileURL).read())
        f.close()
    print("Done")
else:

    # The driver already exists on disk (second time the script is launched). We still have to check if it has been altered
    print("The file already exists in the temporary path, calculating it's checksum...", end='')
    original_md5 = "4e2dc194c2fe98de9c87e2753e8ba3ad"
    with open(FileFullPath, "rb") as filetocheck:
        data = filetocheck.read()
        md5_returned = hashlib.md5(data).hexdigest()

        if md5_returned == original_md5:

            # The hash of the file matches the pre-calculated one
            print("Done")
        else:

            # There was a mismatch with the pre-calculated hash. The file has been altered. We need to download it again.
            print("Failed.")
            print("It should have been " + original_md5 + "and it was " + md5_returned)
            print("Deleting the file...", end='')
            os.remove(FileFullPath)
            print("Done")

            # Downloading the driver from the server
            print("Downloading driver image from server...", end='')
            with open(FileFullPath, 'wb') as f:
                f.write(urllib2.urlopen(FileURL).read())
                f.close()
            print("Done")

# Time to work on the CUPS system to install the printer
Stop_CUPS()
Enable_DEBUG_on_CUPS()
Start_CUPS()

# Checking if the printer is already installed and remove it if necessary
Check_Previous_Installation()

# Printer installation
Install_Printer()

# Submit and get dummy print job to get everything in place
Submit_Dummy_Job()
Retract_Dummy_Job()

# Relaunch CUPS and turn off debug logging
Stop_CUPS()
Disable_DEBUG_on_CUPS()
Start_CUPS()

# Check if the user would like to store his credentials into Keychain
if (ShouldStoreCredentials()):
    Store_Credentials()

# End
print('*'*80)
print("The installation process finished successfully.")
print('*'*80)