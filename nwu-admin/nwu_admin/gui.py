#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright (C) 2006 Yves Junqueira (yves@cetico.org)
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

import gtk
import gtk.glade
import gobject
from M2Crypto import SSL
from M2Crypto.m2xmlrpclib import Server, SSL_Transport

class nwu_data:
    """Setups an interface to the nwu server using XML-RPC
    """
    
    def __init__(self):
        # FIXME: do not hardcode the server_uri
        server_uri = 'https://localhost:8088'
        # FIXME: do not hardcode auth info
        self.auth = ['yvesjm', 'bla']
        self.rpc = self._XClient(server_uri)
        self.computers = self.rpc.get_info(self.auth, 'computers')
        self.tasks = self.rpc.get_info(self.auth, 'tasks')
        print "comps", self.computers
       
    def computer_remove(self, computer_id):
        self.rpc.computer_del(self.auth,computer_id)

    def _XClient(self, server_uri):
        ctx = SSL.Context('sslv3')
        #ctx.load_cert_chain('/tmp/server.pem')
        #ctx.set_allow_unknown_ca(1)
    #    ctx.load_cert('/tmp/server.pem')
    #    ctx.load_verify_info('/tmp/cacert.pem')
    #    ctx.load_client_ca('/tmp/cacert.pem')
        #print "ve1"
        #ctx.set_verify(SSL.verify_peer, 10)
        #print "ve2"
        xs = Server(server_uri, SSL_Transport(ctx))
        return xs

class ui_computers:
    """Build the GTK interface for Nwu Admin, using Glade interface
    file.
    
    The listcomputers.glade file must be located in glade/listcomputers.glade
    at the current directory.
    """

    def __init__(self):

        self.data = nwu_data()
        self.computers= self.data.computers
        self.gladefile = gtk.glade.XML("glade/listcomputers.glade")
        self.listcomputers = self.gladefile.get_widget('treeview1')
        self.listcomputers_model=gtk.TreeStore(gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    )
        self.listcomputers.set_model(self.listcomputers_model)

        self.computers_popup= self.gladefile.get_widget('menu14')
        self.remove_ok = self.gladefile.get_widget('remove_ok')
        self.remove_ok.hide()
        #print "aqui"
        self.signals = { 
            "on_main_destroy" : gtk.main_quit,
            "on_reload_clicked" : self.computers_reload,
            #"on_treeview1_button_press_event" : 
            #    self.on_treeview1_button_press_event, 
#            "on_treeview1_cursor_changed" :
#                self.on_treeview1_cursor_changed,
            "on_update1_clicked": (self.on_update1_clicked, self.listcomputers),
            "on_remove1_clicked": (self.on_remove1_clicked, self.listcomputers),
            "on_remove_cancel_clicked" : self.on_remove_cancel_clicked,
            "on_remove_ok_closed" : self.on_remove_ok_closed,
            "on_remove_ok_destroy_event" : self.on_remove_ok_closed,
            }


        self.gladefile.signal_autoconnect(self.signals)
    def on_treeview1_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.computers_popup.popup( None, None, None, event.button, time) 
            print "event"
            print event.type
            print event.button
        return 1
    
    def insert_computer(self, model,parent,hostid,hostname,os_name, os_version):
        myiter=model.insert_after(parent,None)
        model.set(myiter, 0, hostid, 1, hostname, 2, os_name, 3, os_version)
        print "+computer:", 0, hostid, 1, hostname, 2, os_name, 3, os_version
        #model.set_value(myiter,0,hostid)
        #model.set_value(myiter,1,hostname)
        #model.set_value(myiter,2,os_name)
        #model.set_value(myiter,3,os_version)
        return myiter
   
    def fill_computers(self):
         for computer in self.computers:
            self.insert_computer(self.listcomputers_model, None, \
            computer['id'], computer['hostname'], computer['os_name'],
            computer['os_version'])

    def computers_reload(self, *args):
        print "reload"
        self.data = nwu_data()
        self.computers= self.data.computers
        self.listcomputers_model.clear()
        self.fill_computers()    
        self.listcomputers.show()
#       print model
#        print iter
 
    
    def on_remove_ok_closed(self, button):
        self.remove_ok.hide()
#        self.remove_ok.destroy()
        pass

    def on_remove_cancel_clicked(self, button):
        self.remove_ok.hide()
#        self.remove_ok.destroy()
        pass

    def on_remove1_clicked(self, button, model):
        remove_ok = self.gladefile.get_widget('remove_ok')
        res = remove_ok.run()
        if res == gtk.RESPONSE_OK:
            print "respondeu ok"
            selection = model.get_selection()
            model, iter = selection.get_selected()
            if iter:
                computer_id = model.get_value(iter, 0)
                # Ask the server to remove the computer from the database
                self.data.computer_remove(computer_id)
                model.remove(iter)
        remove_ok.hide()
        return 1
  
    def on_update1_clicked(self, button, model):
        print "click"
        selection = model.get_selection()
        model, iter = selection.get_selected()
        if iter:
            computer_id = model.get_value(iter, 0)
            print "computer id:", computer_id
            new_task = { 'computer_id' : computer_id,
                        'task_name' : 'update'
                        }
            self.data.rpc.task_append(self.auth, new_task)
            #model.remove(iter)

    def main(self):
        # model
        # titles
        i = 0
        for title in ['ID', 'hostname', 'OS name', 'OS version']:
            renderer=gtk.CellRendererText()
            column=gtk.TreeViewColumn(title,renderer, text=i)
            self.listcomputers.append_column(column)
            i += 1
        
        #self.listcomputers.show()
        self.fill_computers()

        gtk.main() 
           


