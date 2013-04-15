#!/usr/bin/python

"""
Tartarus v0.3 - HTTP/HTML Form Dictionary Brute Force Tool
Copyright (C) 2013 Encription Ltd

This is a penetration testing tool, and should therefore not be used to attack targets without prior consent. It is the end user's responsibility to obey all applicable laws. Encription Ltd assume no liability and are not responsible for any misuse or damage caused by this program.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""

import pygtk
import gtk
import mechanize
import gobject
import re
import os
import httplib2
import threading
import Queue
import types
from urllib import urlencode

class GUI:

	def MessageBox(self,message):
		dialog = gtk.MessageDialog(
			None,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_WARNING,
			gtk.BUTTONS_OK,
			None)
		dialog.set_position(gtk.WIN_POS_CENTER)
		dialog.set_markup(message)
		response=dialog.run()
		dialog.destroy()
		return response


	def __init__( self ):
			self.builder = gtk.Builder()
			self.builder.add_from_file("gui.glade")
			self.MainWindow = self.builder.get_object( "MainWindow" )
			self.builder.connect_signals(self)

			self.available_forms = gtk.ListStore(str)
	
			self.formcb = self.builder.get_object("available_forms")
			self.formcb.set_model(self.available_forms)
			formcell = gtk.CellRendererText()
			self.formcb.pack_start(formcell)
			self.formcb.add_attribute(formcell,'text',0)

			self.parameters= self.builder.get_object("parameters")
			C_DATA_COLUMN_NUMBER_IN_MODEL = 0
			parametercell0 = gtk.CellRendererText()
			parametercell1 = gtk.CellRendererText()
			parametercell2 = gtk.CellRendererToggle()
			parametercell3 = gtk.CellRendererToggle()
			parametercell0.set_property('editable', True)
			parametercell1.set_property('editable', True)
			parametercell2.set_radio(True)
			parametercell3.set_radio(True)
			parametercell0.connect('edited', self.cell_edited_callback,0)
			parametercell1.connect('edited', self.cell_edited_callback,1)
			parametercol0 = gtk.TreeViewColumn("Name", parametercell0, text=0)
			parametercol1 = gtk.TreeViewColumn("Value", parametercell1, text=1)
			parametercol2 = gtk.TreeViewColumn("Username", parametercell2,active=2)
			parametercol3 = gtk.TreeViewColumn("Password", parametercell3,active=3)			

			self.parameters.append_column(parametercol0)
			self.parameters.append_column(parametercol1)
			self.parameters.append_column(parametercol2)
			self.parameters.append_column(parametercol3)
			self.parameterstore = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_BOOLEAN,gobject.TYPE_BOOLEAN)
			self.parameters.set_model(self.parameterstore)

			self.parameters.connect("button-press-event",self.treeview_click_handler)
			parametercell2.connect("toggled",self.toggle_callback,2)
			parametercell3.connect("toggled",self.toggle_callback,3)			


			self.resultfields= self.builder.get_object("results")
			C_DATA_COLUMN_NUMBER_IN_MODEL = 0
			resultcell0 = gtk.CellRendererText()
			resultcell1 = gtk.CellRendererText()
			resultcol0 = gtk.TreeViewColumn("Username", resultcell0, text=0)
			resultcol1 = gtk.TreeViewColumn("Password", resultcell1, text=1)

			self.resultfields.append_column(resultcol0)
			self.resultfields.append_column(resultcol1)
			self.resultstore = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
			self.resultfields.set_model(self.resultstore)

			self.builder.get_object("stop_button").set_sensitive(False)
			self.builder.get_object("parameters").set_sensitive(False)

			self.builder.get_object("sc_not_found").set_active(True)
			self.builder.get_object("un_list_radio").set_active(True)
			self.builder.get_object("pw_list_radio").set_active(True)
			self.builder.get_object("sc_text_radio").set_active(True)

			self.selected_form=None

	def treeview_click_handler(self, treeview, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			pthinfo = treeview.get_path_at_pos(x, y)
			
			popup_menu = gtk.Menu()
			add_item = gtk.MenuItem("Add")
			popup_menu.append(add_item)
			add_item.show()
			add_item.connect("activate",self.add_clicked_callback)

			if pthinfo:

				path, col, cellx, celly = pthinfo
				treeview.grab_focus()
				treeview.set_cursor( path, col, 0)
				delete_item = gtk.MenuItem("Delete")
				popup_menu.append(delete_item)
				delete_item.show()
				delete_item.connect("activate",self.delete_clicked_callback)
				
			popup_menu.popup( None, None, None, event.button, event.time)

	def toggle_callback(self,cellrenderer,path,column):
		self.parameterstore.set_value(self.parameterstore.get_iter(path), column, not cellrenderer.get_active())
		for row in self.parameterstore:
			if int(row.path[0]) == int(path):
				row[column]=True
			else:
				row[column]=False			

	def add_clicked_callback(self,button):
		self.parameterstore.append(["New Parameter","New Value",False,False])

	def delete_clicked_callback(self,button):
		selection = self.parameters.get_selection()
		(model, iter) = selection.get_selected()
		self.parameterstore.remove(iter)

	def cell_edited_callback(self,cell,path,data,user_data):
		selection = self.parameters.get_selection()
		(model, iter) = selection.get_selected()
		self.parameterstore.set(iter,user_data,data)


	def load_button(self,data):
		self.available_forms.clear()
		self.parameterstore.clear()


		url=self.builder.get_object("url_entry").get_text()

		try:
			browser=mechanize.Browser()
			browser.addheaders=[("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0")]
			browser.open(url)
			self.forms = [form for form in browser.forms()]
		
			if len(self.forms) == 0:
				self.MessageBox("No Forms Found at Target URL")
				return		

			for form in self.forms:
				self.available_forms.append([form.method+" - "+form.action])

			self.formcb.set_active(0)
		except:
			self.MessageBox("Cannot Load Form - Page Not Found")
		

	def form_changed(self,data):
	 	self.parameterstore.clear()

		self.selected_form=self.forms[self.formcb.get_active()]

		for control in self.forms[self.formcb.get_active()].controls:
			if control.type != None and control.name != None:
				self.parameterstore.append([control.name,None,False,False])

		self.parameters.set_sensitive(True)



	def open_un(self,data):
		chooser = gtk.FileChooserDialog(title="Select Username File",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		response=chooser.run()
		if response == gtk.RESPONSE_OK:
			self.builder.get_object("un_list").set_text(chooser.get_filename())
		chooser.destroy()

	def open_pw(self,data):
		chooser = gtk.FileChooserDialog(title="Select Password File",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		response=chooser.run()
		if response == gtk.RESPONSE_OK:
			self.builder.get_object("pw_list").set_text(chooser.get_filename())
		chooser.destroy()


	def sc_radio_changed(self,data):
		if self.builder.get_object("sc_regex_radio").get_active():
			self.builder.get_object("sc_text").set_text("")
			self.builder.get_object("sc_text").set_sensitive(False)
			self.builder.get_object("sc_regex").set_sensitive(True)
		else:
			self.builder.get_object("sc_regex").set_text("")
			self.builder.get_object("sc_regex").set_sensitive(False)
			self.builder.get_object("sc_text").set_sensitive(True)

	def un_radio_changed(self,data):
		if self.builder.get_object("un_list_radio").get_active():
			self.builder.get_object("un_button").set_sensitive(True)
			self.builder.get_object("un_list").set_sensitive(True)
			self.builder.get_object("un_single").set_sensitive(False)
			self.builder.get_object("un_single").set_text("")
		else:
			self.builder.get_object("un_list").set_text("")
			self.builder.get_object("un_list").set_sensitive(False)
			self.builder.get_object("un_button").set_sensitive(False)
			self.builder.get_object("un_single").set_sensitive(True)

	def pw_radio_changed(self,data):
		if self.builder.get_object("pw_list_radio").get_active():
			self.builder.get_object("pw_button").set_sensitive(True)
			self.builder.get_object("pw_list").set_sensitive(True)
			self.builder.get_object("pw_single").set_sensitive(False)
			self.builder.get_object("pw_single").set_text("")
		else:
			self.builder.get_object("pw_list").set_text("")
			self.builder.get_object("pw_list").set_sensitive(False)
			self.builder.get_object("pw_button").set_sensitive(False)
			self.builder.get_object("pw_single").set_sensitive(True)
	
	def start(self,data):
		ready=True
		self.stop_attack=False
		self.progress=0
		self.resultstore.clear()
		usernames=0
		passwords=0


		username_ready=False
		password_ready=False
		unique_un_pw=True

		for row in self.parameterstore:
			if row[2]:
				username_ready=True
			if row[3]:
				password_ready=True

			if row[2] and row[3]:
				unique_un_pw=False
			
				


		if len(self.available_forms) == 0:
			self.MessageBox("A Target Form Has Not Been Selected")
			ready=False			
		elif not username_ready:
			self.MessageBox("A Username Has Not Been Selected")
			ready=False
		elif not password_ready:
			self.MessageBox("A Password Has Not Been Selected")
			ready=False
		elif not unique_un_pw:
			self.MessageBox("Username and Password Must Use Different Fields")
			ready=False
		elif self.builder.get_object("un_list_radio").get_active() and self.builder.get_object("un_list").get_text() == "":
			self.MessageBox("No Username File Set")
			ready=False
		elif self.builder.get_object("un_single_radio").get_active() and self.builder.get_object("un_single").get_text() == "":
			self.MessageBox("No Username Value Set")
			ready=False
		elif self.builder.get_object("pw_list_radio").get_active() and self.builder.get_object("pw_list").get_text() == "":
			self.MessageBox("No Password File Set")
			ready=False
		elif self.builder.get_object("pw_single_radio").get_active() and self.builder.get_object("pw_single").get_text() == "":
			self.MessageBox("No Password Value Set")
			ready=False
		elif self.builder.get_object("sc_text_radio").get_active() and self.builder.get_object("sc_text").get_text() == "":
			self.MessageBox("No Search Text Set")
			ready=False
		elif self.builder.get_object("sc_regex_radio").get_active() and self.builder.get_object("sc_regex").get_text() == "":
			self.MessageBox("No Search RegEx Set")
			ready=False
		
		if ready:
			self.disable()

			username_field=str()
			password_field=str()

			for row in self.parameterstore:
				if row[2]==True:
					username_field=row[0]
				elif row[3]==True:
					password_field=row[0]

			if self.builder.get_object("sc_regex_radio").get_active():
				search=re.compile(self.builder.get_object("sc_regex").get_text())
			else:
				search=self.builder.get_object("sc_text").get_text()
			
			if self.builder.get_object("un_list_radio").get_active():
				username=open(self.builder.get_object("un_list").get_text(),"r")
			else:
				username=[self.builder.get_object("un_single").get_text()]

			if self.builder.get_object("pw_list_radio").get_active():
				password=open(self.builder.get_object("pw_list").get_text(),"r")
			else:
				password=[self.builder.get_object("pw_single").get_text()]

			if self.builder.get_object("sc_found").get_active():
				found=True
			else:
				found=False

			

			target=Target(self.selected_form,username_field,password_field,dict([(item[0],item[1]) for item in self.parameterstore]),search,found,"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0")
			self.worker_thread=WorkerThread(username,password,target,self.update_label,self.update_table,self.stop)
			self.worker_thread.start()


	def stop(self,data):
		self.worker_thread.stop()
		self.worker_thread.join()
		self.enable()
		
	def Quit_handler(self,data):
		self.stop_attack=True
		gtk.main_quit()

	def enable(self):
		self.builder.get_object("url_entry").set_sensitive(True)
		self.builder.get_object("load_button").set_sensitive(True)
		self.builder.get_object("available_forms").set_sensitive(True)
		self.builder.get_object("parameters").set_sensitive(True)
		self.builder.get_object("un_list_radio").set_sensitive(True) 
		self.builder.get_object("un_single_radio").set_sensitive(True) 
		self.builder.get_object("pw_list_radio").set_sensitive(True) 
		self.builder.get_object("pw_single_radio").set_sensitive(True)
		self.builder.get_object("sc_text_radio").set_sensitive(True) 
		self.builder.get_object("sc_regex_radio").set_sensitive(True)
		
		if self.builder.get_object("un_list_radio").get_active():
			self.builder.get_object("un_button").set_sensitive(True)
			self.builder.get_object("un_list").set_sensitive(True)
		else:
			self.builder.get_object("un_single").set_sensitive(True)
	
		if self.builder.get_object("pw_list_radio").get_active():
			self.builder.get_object("pw_button").set_sensitive(True)
			self.builder.get_object("pw_list").set_sensitive(True)
		else:
			self.builder.get_object("pw_single").set_sensitive(True)

		self.builder.get_object("sc_not_found").set_sensitive(True)
		self.builder.get_object("sc_found").set_sensitive(True)

		if self.builder.get_object("sc_regex_radio").get_active():
			self.builder.get_object("sc_regex").set_sensitive(True)
		else:
			self.builder.get_object("sc_text").set_sensitive(True)

		self.builder.get_object("stop_button").set_sensitive(False)
		self.builder.get_object("start_button").set_sensitive(True)

	def disable(self):
		self.builder.get_object("url_entry").set_sensitive(False)
		self.builder.get_object("load_button").set_sensitive(False)
		self.builder.get_object("available_forms").set_sensitive(False)
		self.builder.get_object("parameters").set_sensitive(False)
		self.builder.get_object("un_list_radio").set_sensitive(False) 
		self.builder.get_object("un_single_radio").set_sensitive(False) 
		self.builder.get_object("pw_list_radio").set_sensitive(False) 
		self.builder.get_object("pw_single_radio").set_sensitive(False)
		self.builder.get_object("sc_text_radio").set_sensitive(False) 
		self.builder.get_object("sc_regex_radio").set_sensitive(False)
		self.builder.get_object("un_button").set_sensitive(False)
		self.builder.get_object("un_list").set_sensitive(False)
		self.builder.get_object("un_single").set_sensitive(False)
		self.builder.get_object("pw_button").set_sensitive(False)
		self.builder.get_object("pw_list").set_sensitive(False)
		self.builder.get_object("pw_single").set_sensitive(False)
		self.builder.get_object("sc_not_found").set_sensitive(False)
		self.builder.get_object("sc_found").set_sensitive(False)
		self.builder.get_object("sc_regex").set_sensitive(False)
		self.builder.get_object("sc_text").set_sensitive(False)

		self.builder.get_object("stop_button").set_sensitive(True)
		self.builder.get_object("start_button").set_sensitive(False)

	def update_label(self,text,progress,total):
		self.builder.get_object("progressbar").set_text(text)
		if total==0:
			self.builder.get_object("progressbar").set_fraction(0)
		else:
			self.builder.get_object("progressbar").set_fraction((float(progress)/float(total)))

	def update_table(self,username,password):
		self.resultstore.append([username,password])		
	
class Target():
	
	def __init__(self,form,username_field,password_field,other_data,search,found,user_agent):
		self.form=form
		self.username_field=username_field
		self.password_field=password_field
		self.other_data=other_data
		self.search=search
		self.user_agent=user_agent
		self.found=found


class WorkerThread(threading.Thread):
		

	def __init__(self,usernames,passwords,target,update_label,update_table,stop_function):
		self.usernames=usernames
		self.passwords=passwords
		self.finished=False
		self.threads=[]
		self.target=target
		self.update_label=update_label
		self.update_table=update_table
		self.stop_function=stop_function
		threading.Thread.__init__(self)

	def run(self):
		gobject.idle_add(self.update_label,"Calculating Search Space",0,0)
		if type(self.passwords) == types.FileType:
			password_length=sum(1 for line in self.passwords)
			self.passwords.seek(0)
		else:
			password_length=len(self.passwords)

		if type(self.usernames) == types.FileType:
			username_length=sum(1 for line in self.usernames)
			self.usernames.seek(0)
		else:
			username_length=len(self.usernames)

		total_count=username_length*password_length			

		gobject.idle_add(self.update_label,"Starting",0,0)
		queue=Queue.Queue(100)
		
		for _ in range(20):
			thread=BruteForcer(queue,self.target,self.update_table)
			self.threads.append(thread)
			thread.start()
		
		username_count=0
		password_count=0
		display_interval=0
		

		for username in self.usernames:
			if self.finished:
				break

			for password in self.passwords:
				password_count+=1
				if self.finished:
					break

				enqueued=False
				while not enqueued:
					try:				
						if self.finished:
							break
						queue.put_nowait((username.strip(),password.strip()))
						enqueued=True
					except Queue.Full:
						pass
				

				if display_interval == 5:
					display_interval=0
					gobject.idle_add(self.update_label,"Running - "+str(password_count)+"/"+str(total_count),password_count,total_count)
				else:
					display_interval+=1

			if type(password) == types.FileType:			
				password.seek(0)
		
					
		for thread in self.threads:
			thread.stop()
			thread.join()
		gobject.idle_add(self.update_label,"Stopped",0,0)
		gobject.idle_add(self.stop_function,None)

	def stop(self):
		self.finished=True
		

class BruteForcer(threading.Thread):
	


	def __init__(self,queue,target,update_table):
		self.queue=queue
		self.target=target
		self.finished=False
		self.update_table=update_table
		threading.Thread.__init__(self)

	def run(self):

		http_connection=httplib2.Http(disable_ssl_certificate_validation=True)

		while True:
			try:
				if self.finished:
					break			
	
				username,password=self.queue.get_nowait()
							
				if self.target.form.method == "POST":
					headers={"Content-Type":"application/x-www-form-urlencoded"}
				else:
					headers={}

				response,content=http_connection.request(self.target.form.action,self.target.form.method,urlencode(dict(self.target.other_data.items()+[(self.target.username_field,username),(self.target.password_field,password)])),headers=headers)
				
				if type(self.target.search) == types.StringType:
					if self.target.found:
						if self.target.search in content:
							gobject.idle_add(self.update_table,username,password)
					else:
						if self.target.search not in content:
							gobject.idle_add(self.update_table,username,password)
				else:
					if self.target.found:
						if self.target.search.match(content):
							gobject.idle_add(self.update_table,username,password)
					else:
						if not self.target.search.match(content):
							gobject.idle_add(self.update_table,username,password)
			except Queue.Empty:
				pass

	def stop(self):
		self.finished=True


gui = GUI()
gtk.gdk.threads_init()
gui.MainWindow.show_all()
gtk.main()
