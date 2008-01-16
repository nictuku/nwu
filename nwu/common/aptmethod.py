#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2008 Stephan Peijnik (sp@gnu.org)
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

import sys

class AptMethod:
    def __init__(self, version):
        self.version = version
        self.capabilities = {}
        self.running = False

    def set_capability(self, name, value):
        if not self.running:
            self.capabilities[name] = value
        else:
            raise Exception('Cannot set capability whilst method is running.')

    def write(self, data):
        return sys.stdout.write(data)

    def writeline(self, line):
        return self.write(line + '\n')

    def flush(self):
        try:
            return sys.stdout.flush()
        except KeyboardInterrupt:
            sys.exit(0)

    def readline(self):
        try:
            return sys.stdin.readline()
        except KeyboardInterrupt:
            sys.exit(0)

    def send_reply(self, msg_code, msg_string, headers={}):
        self.writeline('%d %s' % (msg_code, msg_string))
        for h in headers:
            self.writeline('%s: %s' % (h, headers[h]))
        self.write('\n')
        self.flush()

    def send_capabilities(self):
        """ Send capabilities. 
        
        This initializes a session.
        """
        headers = {'Version': self.version, 'Single-Instance': 'true'}
        headers.update(self.capabilities)
        self.send_reply(100, 'Capabilities', headers)
    
    def send_log(self, message):
        """ Send log message.

        This causes apt, if debugging is enabled, to display the message.
        """
        self.send_reply(101, 'Log', {'Message': message})

    def send_status(self, message):
        """ Send status message.

        Used for displaying pre-transfer status messages.
        """
        self.send_reply(102, 'Status', {'Message': message})

    def send_uri_start(self, uri, size, lastmod, resumepoint):
        headers = {
            'URI': uri,
            'Size': size,
            'Last-Modified': lastmod,
            'Resume-Point': resumepoint
            }
        self.send_reply(200, 'URI Start', headers)

    def send_uri_done(self, uri, size, lastmod, filename, md5hash):
        headers = {
            'URI': uri,
            'Size': size,
            'Last-Modified': lastmod,
            'Filename': filename,
            'MD5-Hash': md5hash
            }
        self.send_reply(201, 'URI Done', headers)

    def send_uri_failure(self, uri, message):
        headers = {
            'URI': uri,
            'Message': message
            }
        self.send_reply(400, 'URI Failure', headers)

    def send_failure(self, message):
        self.send_reply(401, 'General Failure', {'Message': message})

    def send_auth_required(self, site):
        self.send_reply(402, 'Authorization Required', {'Site': site})
    
    def send_media_failure(self, media, drive):
        self.send_reply(403, 'Media Failure', {'Media': media, 'Drive': drive})

    def handle_other(self, msg_code, msg_string, headers):
        self.send_failure('Handler for %d (%s) not implemented.' 
                          % (msg_code, msg_string))

        sys.stderr.write('ERROR: unhandled message\n')
        sys.stderr.write('msg_code  : %s\n' % (msg_code))
        sys.stderr.write('msg_string: %s\n' % (msg_string))
        sys.stderr.write('headers   : %s\n' % (headers))
        sys.stderr.flush()

    def run(self):
        self.running = True

        # First thing we should do is writing out our capabilities...
        self.send_capabilities()

        while not sys.stdin.closed:
            have_full_request = False
            message_code = None
            message_string = None
            message_headers = {}

            while not have_full_request:
                if sys.stdin.closed:
                    return

                line = self.readline()
                if line == '':
                    break

                line = line.strip()

                if not message_code and ' ' in line:
                    try:
                        message_code, message_string = line.split(' ', 1)
                        message_code = int(message_code)
                    except Exception, e:
                        self.send_failure('Internal error.')
                elif line != '':
                    header_name = None
                    header_value = None
                    header_name, header_value = line.split(': ', 1)
                    message_headers[header_name] = header_value
                elif line == '' and message_code:
                    have_full_request = True
                else:
                    self.send_failure('Internal error.')

            # we should have a full request at this point.
            if have_full_request:
                func = getattr(self, 'handle_%d' % (message_code), None)
                if func:
                    func(message_string, message_headers)
                else:
                    self.handle_other(message_code, message_string, 
                                      message_headers)

    def convert_truefalse(self, truefalse):
        if truefalse == 'true':
            return True
        return False

    def handle_600(self, msg_string, headers):
        """
        URI Acquire request. This method needs to be overridden!

        This request should provide us with the following 
        headers:
        Index-File  Requested file is index file (true|false).
        URI         URI of file.
        Filename    Local filename to save file to.
        """
        self.send_uri_failure(headers['URI'], 'handle_600 method not '
                              'implemented.')


if __name__ == '__main__':
    AptMethod('1.0').run()
