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

"""
This module contains shared code used by both the RPC server and client.
"""

from xmlrpclib import Fault as xmlrpcFault, _Method
from nwu.common.SecureXMLRPC import SecureProxy

__all__ = ['RPCFault', 'RPCProxy', 'UnknownMethodFault', 'AccessDeniedFault',
           'NotPossibleFault', 'NotFoundFault', 'InvalidParamsFault']

Fault = xmlrpcFault

class RPCFault:
    """ RPC error codes """
    GENERIC_FAULT = 1
    UNKNOWN_METHOD = 2
    ACCESS_DENIED = 3
    NOT_POSSIBLE = 4
    NOT_FOUND = 5
    INVALID_PARAMS = 6
    INTERNAL_FAULT = 7
    
    # Table for reverse-lookups.
    # This allows us to re-generate the original faults (correct class)
    # in clients.
    LOOKUP_TABLE = ['Fault', 'UnknownMethodFault', 'AccessDeniedFault',
                    'NotPossibleFault', 'NotFoundFault', 'InvalidParamsFault']

    @staticmethod 
    def translate_fault(generic_fault):
        """ Translate generic fault to specific RPC fault (using faultCode) """
        fault_class = None

        if generic_fault.faultCode > 1:
            idx = generic_fault.faultCode - 1

            # This could happen in theory...
            if len(RPCFault.LOOKUP_TABLE) > idx:
                fault_class = eval(RPCFault.LOOKUP_TABLE[idx])

        if not fault_class:
            # Re-raise the original fault.
            raise generic_fault
        
        # Raise the translated fault...
        raise fault_class(generic_fault.faultString)
    

class UnknownMethodFault(Fault):
    def __init__(self, method_name):
        Fault.__init__(self, RPCFault.UNKNOWN_METHOD, method_name)

class AccessDeniedFault(Fault):
    def __init__(self, method_name):
        Fault.__init__(self, RPCFault.ACCESS_DENIED, method_name)

class NotPossibleFault(Fault):
    def __init__(self, message):
        Fault.__init__(self, RPCFault.NOT_POSSIBLE, message)

class NotFoundFault(Fault):
    def __init__(self, message):
        Fault.__init__(self, RPCFault.NOT_FOUND, message)

class InvalidParamsFault(Fault):
    def __init__(self, method_name):
        Fault.__init__(self, RPCFault.INVALID_PARAMS, method_name)
    
class InternalFault(Fault):
    def __init__(self):
        Fault.__init__(self, RPCFault.INTERNAL_FAULT, 'Internal error.')

class RPCProxy(SecureProxy):
    """ Override SecureProxy to provide Fault translation. """
    def __getattr__(self, name):
        return _Method(self.__request, name)

    def __request(self, methodname, params):
        try:
            # XXX: Using _ServerProxy__request is an evil workaround.
            return self._ServerProxy__request(methodname, params)
        except Fault, f:
            # Try to translate the fault.
            RPCFault.translate_fault(f)
