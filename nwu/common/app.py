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

from nwu.common.config import Config

class Option:
    """ Command line option """
    def __init__(self, long_name, help, short_name=None, argument=False,
                 default=None, valid_values=None):
        self.long_name = long_name
        self.short_name = short_name
        self.argument = argument
        self.help = help
        self.present = False
        self.value = default
        self.valid_values = valid_values

class Command:
    """ Command base class.
    
    If not extended it works as a command container.
    If you want a simple command you only have to override the execute()
    method."""
    def __init__(self, name=None, parent=None, help=''):
        """ Initializes Command class.

        Note: The parent argument should be present for all non-root
              commands.
        """
        self.name = name
        self.parent = parent
        self.help = help
        self.commands = {}
        self.options = {}

    def register_command(self, name, handler):
        """ Registers a new sub-command, used by Command container class. """
        self.commands[name] = handler

    def execute_command(self, app, args=[]):
        """ Executes command.

        NOTE: Do NOT override this method as it does all options parsing
        and calls execute() in turn.
        """
        unhandled_args = self.parse_options(app, args)
        cmd_name = None

        if unhandled_args:
            for a in unhandled_args:
                if a[0] != '-':
                    cmd_name = a
                    unhandled_args.remove(a)
                    break

        if cmd_name == 'help':
            return self.show_help(app)

        return self.execute(app, unhandled_args, cmd_name)

    def execute(self, app, args, cmd_name=None):
        """ Command code.

        This method can be overridden to provide custom behaviour.
        It usually contains the implementation of the command.
        """
        if not cmd_name:
            return self.show_help(app, 'No command supplied.')

        if not cmd_name in self.commands:
            return self.show_help(app, 'Unknown command: %s' % (cmd_name))

        cmd = self.commands[cmd_name]
        return cmd.execute_command(app, args)

    def register_option(self, long_name, help, short_name=None, argument=False,
                        default=None, valid_values=None):
        """ Registers a command line option. """
        self.options[long_name] = Option(long_name, help, short_name, argument,
                                         default=default, 
                                         valid_values=valid_values)

    def find_option(self, name, short=False):
        """ Used internally """
        if not short:
            if name in self.options:
                return self.options[name]
            else:
                return None

        for opt_name in self.options:
            o = self.options[opt_name]
            if o.short_name == name:
                return o
        return None

    def option_is_set(self, name):
        """ Checks if an option (identified by its longName) was set on the
        commandline.
        """
        if not name in self.options:
            return False
        return self.options[name].present

    def option_get_value(self, name):
        """ Gets the value of the argument passed with an option.

        Returns None for options which were not set and for options
        which do not require an argument.
        """
        return self.options[name].value

    def parse_options(self, app, args):
        """ Option parser. """
        unhandled_args = []

        for arg in args:
            value = None
            name = None

            # options are prefixed by '-'
            if arg[0] == '-':
                short = False

                # long option
                if arg[1] == '-':
                    names = [arg[2:],]

                # short option
                else:
                    short = True
                    if '=' in arg[1:]:
                        names = [arg[1:]]
                    else:
                        names = arg[1:]
                
                # support for multiple short options
                for name in names:

                    # option with a value?
                    if '=' in name:
                        name, value = name.split('=', 1)
                    
                    # This only happens with multiple short options and a value
                    if short and len(name) > 1:
                        return self.show_help(app, '%s option cannot be '\
                                                  'combined with other short '\
                                                  'options because it '\
                                                  'requires a value.' \
                                             % (name[0]))
                    # next step: find option...
                    opt = self.find_option(name, short)

                    if not opt:
                        unhandled_args.append(arg)
                    else:
                        # found option, need to handle it
                        opt.present = True

                        if opt.argument and not value:
                            return self.show_help(app, '%s option requires ' \
                                                  'a value.' % (name))

                        if opt.valid_values and value not in opt.valid_values:
                            return self.show_help(app, 
                                'Invalid value specified for %s. ' \
                                'Valid arguments:\n %s' % (name, 
                                    ", ".join(opt.valid_values)))
                        opt.value = value
            else:
                unhandled_args.append(arg)

        return unhandled_args

    def get_name(self):
        """ Return 'fully qualified' command name. """
        if not self.name:
            return ''

        if self.parent and self.parent.get_name() != '':
            par_name = self.parent.get_name()
            return '%s %s' % (par_name, self.name)
        return self.name

    def show_help(self, app, message=None):
        """ Display help for command. """
        print app.usage_header() + '\n'

        if message:
            if len(message) > 77:
                s = '*'
                words = message.split(' ')
                for w in words:
                    if (len(s) + len(w) + 1) <= 79:
                        s += ' ' + w
                        if w[-1] == '\n':
                            # Handle newlines in message.
                            print s[:-1]
                            s = ' '
                    else:
                        print s
                        s = '  ' + w
                print s + '\n'
            else:
                print '* %s\n' % (message)
        
        my_name = self.get_name()
        if not my_name:
            my_name = app.bin_name

        print 'Help for command %s:\n' % (my_name)

        if len(self.options) > 0:
            # find longest option name
            max_length = 0
            for opt_name in self.options:
                o = self.options[opt_name]

                l = len(o.long_name) + 2
                if o.argument:
                    # len('value')
                    l += 6
                max_length = max(l, max_length)
            # len('-x,')
            max_length += 3

            # needed for good-looking indentation
            def print_opt(max_length, opt):
                s = ''
                if opt.short_name:
                    s += '-%s,' % (opt.short_name)
                else:
                    s += '   '
                s += '--%s' % (opt.long_name)

                if opt.argument:
                    s+= '=value'

                for i in range(len(s), max_length):
                    s += ' '
                s += '  '
                base_indent = len(s)
                help_txt = opt.help
                if (len(s) + len(opt.help)) > 79:
                    s = s[:-1]

                    words = help_txt.split(' ')
                    for w in words:
                        if (len(s) + len(w) + 1) <= 79:
                            s += ' ' + w
                        else:
                            print s
                            s = ''
                            for i in range(0, base_indent):
                                s += ' '
                            s += w
                    print s
                else:
                    print '%s%s' % (s, help_txt)

            print 'Following options are available: '
            for opt_name in self.options:
                print_opt(max_length, self.options[opt_name])
            print ''

        if len(self.commands) > 0:
            print 'Following commands are available (%s <command>):\n' \
                % (my_name)
            for c in self.commands:
                print c
            print ''
            print 'More information on every command is available using %s ' \
                '<command> help' % (my_name)

        sys.exit(255)

class Application:
    """ Application base class """
    options = []
    def __init__(self, args=sys.argv[1:], bin_name=sys.argv[0], 
                 root_command_class=Command):
        """ Initializes the application.

        This method should be overridden by child-classes to add 
        per-application initialization code.

        The args argument by default contains sys.argv, but can be filled
        with custom commandline options.
        """
        self.args = args
        self.bin_name = bin_name
        self.config = None
        self.config_file_path = None
        self.root_command = root_command_class()

    def read_config(self):
        """ Reads the config file found at path.

        self.configPath must have been set by the application before in order
        for this to work.
        """
        self.config = Config(self.config_file_path)

    def main(self):
        """ Runs the application.

        This method uses self.root_command to call the correct command.
        """
        self.root_command.execute_command(self, self.args)

    def usage_header(self):
        """Returns the header to display before command help."""
        return '%s help' % (self.bin_name)
