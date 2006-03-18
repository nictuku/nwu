#!/usr/bin/env python

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
        self.rpc = self._XClient(server_uri)
        self.machines = self.rpc.get_info('machines')
        self.tasks = self.rpc.get_info('tasks')
       
    def machine_remove(self, machine_id):
        self.rpc.machine_remove(machine_id)

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

class list_nodes:
    """Build the GTK interface for Nwu Admin, using Glade interface
    file.
    
    The listnodes.glade file must be located in glade/listnodes.glade
    at the current directory.
    """
    nodes = []
    gladefile = None 
    listnodes = None
    listnodes_model = None
    signals = {}
    nodes_popup = object
    remove_ok = object

    def __init__(self):

        self.data = nwu_data()
        self.nodes= self.data.nodes
        self.gladefile = gtk.glade.XML("glade/listnodes.glade")
        self.listnodes = self.gladefile.get_widget('treeview1')
        self.listnodes_model=gtk.TreeStore(gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    )
        self.listnodes.set_model(self.listnodes_model)

        self.nodes_popup= self.gladefile.get_widget('menu14')
        print "nada"
        self.remove_ok = self.gladefile.get_widget('remove_ok')
        self.remove_ok.hide()
        #print "aqui"
        self.signals = { 
            "on_main_destroy" : gtk.main_quit,
            "on_reload_clicked" : self.nodes_reload,
            #"on_treeview1_button_press_event" : 
            #    self.on_treeview1_button_press_event, 
#            "on_treeview1_cursor_changed" :
#                self.on_treeview1_cursor_changed,
            "on_update1_clicked": (self.on_update1_clicked, self.listnodes),
            "on_remove1_clicked": (self.on_remove1_clicked, self.listnodes),
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
                self.nodes_popup.popup( None, None, None, event.button, time) 
            print "event"
            print event.type
            print event.button
        return 1
    
    def insert_node(self, model,parent,hostid,hostname,os_name, os_version):
        myiter=model.insert_after(parent,None)
        model.set(myiter, 0, hostid, 1, hostname, 2, os_name, 3, os_version)
        print "+node:", 0, hostid, 1, hostname, 2, os_name, 3, os_version
        #model.set_value(myiter,0,hostid)
        #model.set_value(myiter,1,hostname)
        #model.set_value(myiter,2,os_name)
        #model.set_value(myiter,3,os_version)
        return myiter
   
    def fill_nodes(self):
         for node in self.nodes:
            self.insert_node(self.listnodes_model, None, node.id, node.hostname,
                node.os_name, node.os_version)

  
    def nodes_reload(self, *args):
        print "reload"
        self.data = nwu_data()
        self.nodes= self.data.nodes
        self.listnodes_model.clear()
        self.fill_nodes()    
        self.listnodes.show()
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
                machine_id = model.get_value(iter, 0)
                # Ask the server to remove the machine from the database
                self.data.machine_remove(machine_id)
                model.remove(iter)
        remove_ok.hide()
        return 1
  
    def on_update1_clicked(self, button, model):
        print "click"
        selection = model.get_selection()
        model, iter = selection.get_selected()
        if iter:
            machine_id = model.get_value(iter, 0)
            print "machine id:", machine_id
            new_task = { 'machine_id' : machine_id,
                        'task_name' : 'update'
                        }
            self.data.rpc.task_append(new_task)
            #model.remove(iter)

    def main(self):
        # model
        # titles
        i = 0
        for title in ['ID', 'hostname', 'OS name', 'OS version']:
            renderer=gtk.CellRendererText()
            column=gtk.TreeViewColumn(title,renderer, text=i)
            self.listnodes.append_column(column)
            i += 1
        
        #self.listnodes.show()
        self.fill_nodes()

        gtk.main() 
           


