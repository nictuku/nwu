#!/usr/bin/env python

import gtk
import gtk.glade
import gobject
import local_data

class list_nodes:
    """Build the GTK interface for Nwu Admin, using Glade interface
    file.
    
    The listnodes.glade file must be located in glade/listnodes.glade
    at the current directory.
    """
    nodes = []
    gladefile = ''
    listnodes = ''
    listnodes_model = '' 
    signals = {}
    data = ''
    nodes_popup = object

    def __init__(self):

        self.data = local_data.nwu_data()
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
        self.signals = { 
            "on_main_destroy" : gtk.main_quit,
            "on_reload_clicked" : self.nodes_reload,
            #"on_treeview1_button_press_event" : 
            #    self.on_treeview1_button_press_event, 
#            "on_treeview1_cursor_changed" :
#                self.on_treeview1_cursor_changed,
            "on_update1_clicked": (self.on_update1_clicked, self.listnodes),
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
        self.data = local_data.nwu_data()
        self.nodes= self.data.nodes
        self.listnodes_model.clear()
        self.fill_nodes()    
        self.listnodes.show()
#       print model
#        print iter
    
    def on_update1_clicked(self, button, model):
        print "click"
        selection = model.get_selection()
        model, iter = selection.get_selected()
        if iter:
            host = model.get_value(iter, 0)
            print "host:", host
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
           


