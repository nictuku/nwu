#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006 José de Paula Eufrásio Junior (jose.junior@gmail.com) AND
#                      Yves Junqueira (yves.junqueira@gmail.com)
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Provides network information for win32 systems
"""

import logging
import sys
import win32com.client
import _winreg as wreg
import socket

class interface:
    """Retrieves interface specific information
    """
    ip_addresses = []
    mac_address = ''
    netmask = ''
    status = ''
    dhcp_server = ''
    ip_network = ''
    interf_dict = {}

    def __init__(self, interf=None):
        self._set_net_info(interf)
        self.ip_addresses = self._net_adapters[0].IPAddress
        self.mac_address = self._net_adapters[0].MACAddress
        self.netmask = self._net_adapters[0].IPSubnet[0]
        self.status = self._net_adapters[0].IPEnabled

    def _set_net_info(self, interf=None):
        strComputer = "."
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(strComputer,"root\cimv2")
        ifaces = objSWbemServices.ExecQuery(
            "Select * from Win32_NetworkAdapterConfiguration"
        )
        net_adapters = []
        default_gateway = []
        dns_resolvers = []
        dns_domain = ''
        for iface in ifaces:
            # FIXME: make sure the other infos below are not None
            if iface.DNSDomain is not None:
                dns_domain = iface.DNSDomain
            
            if (interf and iface.Description.find(interf) > 0) or not interf:
                net_adapters.append(iface)
            foo = iface.DefaultIPGateway
            if foo is not None:
                for gateway in foo:
                    default_gateway.append(gateway)
            dnsfoo = iface.DNSServerSearchOrder
            if foo is not None:
                for server in foo:
                    dns_resolvers.append(server)
                    
        self._net_adapters = net_adapters        
        self.default_gateway = default_gateway
        self.dns_resolvers = dns_resolvers
        self.dns_domain = dns_domain
      
class network(interface):
    """This is the stuff users will access. It inherits data from other 'os' 
    classes so users can access information like network.dnsdomain.
    """
    def __init__(self):
        self.interface = self.interface_wrapper
        self.last_user = self._get_last_user()
        self.hostname = socket.gethostname()
        i = interface()
        self.default_gateway = i.default_gateway
        self.dns_resolvers = i.dns_resolvers
        self.dns_domain = i.dns_domain
                
    def interface_wrapper(self, interf=None):
        i = interface(interf)
        return i

    def _get_last_user(self):
        regpath = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
        reg = wreg.OpenKey(wreg.HKEY_LOCAL_MACHINE, regpath)
        try:
            ret = wreg.QueryValueEx(reg, 'DefaultUserName')
        except:
            return Null
        else:
            return ret[0]

    
        
if __name__ == '__main__':

    g = network()
    print g.dns_resolvers
    #print i.interf_dict
    #print d.dnsdomain, d.dnsresolvers
    b = g.interface()
    print b.ip_addresses
    print g.default_gateway
    print g.dns_domain
    #print "teste", g.interfaces, b.ip_addresses
