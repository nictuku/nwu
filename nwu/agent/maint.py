#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006-2008 Yves Junqueira (yves@cetico.org)
#
#    This file is part of NWU.
#
#    NWU is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    NWU is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with NWU.  If not, see <http://www.gnu.org/licenses/>.

"""Actions run by root from nwu-maint are defined here. It has to be 100%
safe.
"""
import logging
import traceback
import sys


try:
    import subprocess
except ImportError:
    import commands
    old_py = True
else:
    old_py = False

import smtplib

from nwu.common import is_safe

log = logging.getLogger('nwu-maint.agent.maint')
mesg = """To: %s
Subject: NWU %s task failed

The requested task "%s" failed.
See the detailed log below:

"""

def apt_get(operation, **opts):
    """Build a command string to call apt-get.
    """
    # unit test: DONE
    if operation not in ['update', 'upgrade', 'install']:
        raise Exception, "Unknown operation: %s" % operation
    args = []
    if operation == 'install' and (not opts.get('packages', False) 
        or opts['packages'] < 1):
        raise Exception, "Install needs at least an argument"
    if opts.get('trivial_only', False):
        args.append('--trivial-only')
    if opts.get('force_yes', False):
        args.append('--force-yes')
    if opts.get('assume_yes', False):
        args.append('--assume-yes')
    if opts.get('allow_unauthenticated', False):
        args.append('--allow-unauthenticated')
    args.append('%s' % operation)
    if operation == 'install' and opts.get('packages', False):
        for p in opts.get('packages', False):
            args.append('%s' % p)
    command = 'apt-get'
    return (command, args)

def run_apt_get(command, args=[]):
    """Call apt-get using a secure environment.
    """
    # unit test: DONE
    arg_string = " ".join(args).strip()
    log.debug("Running '%s %s'" % (command, arg_string))
    if old_py:
        (ret, out) = commands.getstatusoutput(
    "export LANGUAGE=C; DEBIAN_FRONTEND=noninteractive apt-get %s" % arg_string
            )
    else:
        full_args = [ command ] + args
        try:
            status = subprocess.Popen(
                full_args,
                executable=command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
        #        stdin=open('/dev/null'),
                env={   "LANGUAGE" : 'C',
                        "DEBIAN_FRONTEND" : "noninteractive",
                        "PATH" : "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                        }
                )
            follow = status.stdout
	    out = ''
            while status.poll() == None:
                p = follow.readline()
                if p:
                    log.info("(running): %s" % p.strip())
		    out = out + p
            ret = status.wait()
        except:
            log.error(" ".join(["error while trying to run apt_get", traceback.format_exc()]))
            sys.exit(1)
    syslog_err = []
    #if out:
    #    syslog_err = out.split('\n')
    if ret != 0:
        log.error("Failed to exec '%s'. Return code: %s." % (command, ret))
	# redundant
        # log.error("Output:")
        # for mm in syslog_err:
        #     log.error(mm)
        err_mail = mesg % ('root', command, command)
        err_mail += str(out)
        try:
            mailserver = smtplib.SMTP('localhost')
            mailserver.sendmail('root', 'root', err_mail)
        except:
            log.error(" ".join(["error while trying to send mail: ", traceback.format_exc()]))
    else:
        log.info("Operation '%s' finished." % command)
        for mm in syslog_err:
            log.debug(mm)
    return ret

def rep_valid(repository):
    """Validate repository string.
    """
    # unit test: DONE
    
    # FIXME: use a validational regexp
    if not is_safe(repository,http=True):
        log.warn("Ignoring repository: strange characters")
        return False
    rep_elements = repository.split()
    if len(rep_elements) < 3:
        log.warn("Ignoring repository: missing elements")
        return False
    rep_type = rep_elements[0]
    rep_uri = rep_elements[1]
    rep_distribution = rep_elements[2]
    rep_components = " ".join(rep_elements[3:])
    valid_types = ['deb', 'deb-src']
    if not rep_type in valid_types:
        log.warn("Ignoring repository: rep-type not valid")
        return False
    return True

def rep_add(newrep):
    """Add a new repository to the sources.list file.
    newrep is a dictionary with "type", "uri", "distribution" and "components" keys.
    """
    if rep_valid(newrep):
        # Write to sources.list
        # FIXME: if apt version supports, we could use /etc/apt/sources.list.ld
        log.info("Writing new repository to sources.list")
        src = open('/etc/apt/sources.list', 'a')
        try:
            src.write("\n" + newrep + "\n")
        except:
            log.error("Error adding new rep to sources.list")
            return False
        return True
    else:
        return False
