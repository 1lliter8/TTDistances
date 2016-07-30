import suds
from suds.client import Client
from PyQt4 import QtCore, QtGui, uic
from Queue import Queue # Makes suds requests threadsafe
from contextlib import contextmanager # For suds threadsafe workaround
import sys, threading, time, json, urllib2



"""Loads the .ui file for the GUI"""
form_class = uic.loadUiType('ui3.ui')[0]
intro_class = uic.loadUiType('intro.ui')[0]



class IntroUI(QtGui.QDialog, intro_class):
	"""Gets password, username and API key"""
	def __init__(self, parent = None):
		QtGui.QDialog.__init__(self, parent)
		self.setupUi(self)
		self.ln_pword.setEchoMode(2)
		self.psh_go.clicked.connect(self.getinfo)
		self.psh_cncl.clicked.connect(self.reject)
		self.info = []
		self.cancel = False
		self.testclient = Client("http://www.tickettree.com/service/ttservice.asmx?wsdl")
	
	def getinfo(self):
		uname = self.ln_uname.text()
		pword = self.ln_pword.text()
		api = self.ln_api.text()
		if uname != "" and pword != "":
			self.info = [uname, pword, api]
			try:
				self.testclient.service.GetAllHotels (self.info[0], self.info[1])
			except suds.WebFault:
				QtGui.QMessageBox.critical(self, "TicketTree error", "Login details incorrect, please try again")
			else:
				self.accept()
	
	def quit(self):
		self.cancel = True



class TTUI(QtGui.QWidget, form_class):
	"""Initiates GUI, assigns signals and some values"""
	def __init__(self, info, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.setupUi(self)
		self.threads = []
		self.tt = "" # filled in self.onLoad
		self.ttdaemon = TTDaemon()
		self.google = "" # filled in self.onLoad
		self.checkeditems = {}
		self.info = info

		"""Some raw data insertion"""

		self.listHotels.setColumnCount(7)
		self.listTheatres.setColumnCount(7)
		self.listHotels.setHorizontalHeaderLabels(["", "Hotel name", "Latitude", "Longitude", "City", "Distance from target", "Transport time"])
		self.listTheatres.setHorizontalHeaderLabels(["", "Theatre name", "Latitude", "Longitude", "City", "Distance from target", "Transport time"])
		self.tabWidget.setTabText(1, "Theatres")
		self.tabWidget.setTabText(0, "Hotels")
		self.cities = ["All cities", "Checked items"]
		self.gsType.insertItems(0, ["Walking", "Public transport", "Car", "Bicycle"])

		"""Signal connections"""

		self.gsGet.clicked.connect(self.btn_getdist)
		self.gsSave.clicked.connect(self.btn_save)
		self.ttdaemon.table.connect(self.tableUpdate)
		self.ttdaemon.city.connect(self.cityUpdate)
		self.ttdaemon.progress.connect(self.progressUpdate)
		self.ttdaemon.save.connect(self.saveUpdate)
		self.listHotels.cellChanged.connect(self.tableChecks)
		self.listTheatres.cellChanged.connect(self.tableChecks)
		self.destCity.activated.connect(self.comboChecks)
		self.tabWidget.currentChanged.connect(self.tabChecks)
	
	def onLoad_wrapper(self):
		"""Loads info from TicketTree"""
		loadthread = threading.Thread(target = self.onLoad)
		loadthread.setDaemon(True)
		loadthread.start()
	
	def onLoad(self):
		"""Sets up classes and objects for the GUI"""
		self.tt = TTComms(self.info[0], self.info[1])
		self.google = GoogleComs(self.info[2])
		
		"""Starts a thread that loads data from TicketTree"""
		self.tt.getll_handler(self.threads)
		THREADLIMIT = 75
		loops = len(self.threads) / THREADLIMIT
		if (len(self.threads) % THREADLIMIT) > 0:
			loops += 1
			timesround = 0
			self.ttdaemon.progressUpdate(loops, timesround)

		for i in range(loops):
			start = i * THREADLIMIT
			finish = start + THREADLIMIT
			if finish > len(self.threads):
				finish = start + (len(self.threads) % THREADLIMIT)
			currentloop = self.threads[start:finish]

			done = False
			total = len(currentloop)
			current = 0
			for x in currentloop:
				x.start()
			while not done:
				current = 0
				for x in currentloop:
					if x.is_alive() == False:
						current += 1
				if current == total:
					done = True

			timesround += 1
			self.ttdaemon.progressUpdate(loops, timesround)

		done = False
		while not done:
			threads = self.threads
			ifdone = []
			for i in threads:
				if i.is_alive():
					ifdone.append(True)
			if True in ifdone:
					pass
			else:
				done = True

		self.ttdaemon.tableUpdate()
		self.ttdaemon.cityUpdate()

	def selectTab(self):
		"""Returns the correct dict for the tab that's currently selected"""
		if self.tabWidget.currentIndex() == 0:
			return self.tt.tt_prochotels
		elif self.tabWidget.currentIndex() == 1:
			return self.tt.tt_proctheatres

	def selectData(self):
		"""Takes the currently selected tab and destination options and spits out a list of
		hotels or theatres that the user wants to work with"""
		destination = self.destCity.currentText()
		queriedDestinations = []

		datadict = self.selectTab()
		listview = ""
		if datadict == self.tt.tt_prochotels:
			listview = self.listHotels
		elif datadict == self.tt.tt_proctheatres:
			listview = self.listTheatres

		for i in datadict.keys():
			if destination == "All cities":
				if datadict[i][2] != None:
					queriedDestinations.append(i)
			elif destination == "Checked items":
				for x in range(listview.rowCount()):
					if listview.item(x, 1).text() == datadict[i][1]:
						if listview.item(x, 0).checkState():
							queriedDestinations.append(i)
			elif datadict[i][4] == destination:
				queriedDestinations.append(i)

		return queriedDestinations

	def btn_save(self):
		"""Constructs a JSON object of selected data and saves it"""
		datadict = self.selectTab()

		travelinfo = {}
		travelinfo["locationtype"] = str(self.tabWidget.tabText(self.tabWidget.currentIndex()))
		travelinfo["locationoptions"] = str(self.destCity.currentText())
		travelinfo["traveltype"] = str(self.gsType.currentText())

		destination = {}
		destination[str(self.destName.text())] = {
			"lattitude": str(self.destLat.text()),
			"longitude": str(self.destLon.text())
			}

		queriedDestinations = self.selectData()

		locations = {}
		for i in queriedDestinations:
			locations[datadict[i][1]] = {
				"latitude": datadict[i][2],
				"longitude": datadict[i][3],
				"city": str(datadict[i][4]),
				"distance": str(datadict[i][5]),
				"transporttime": str(datadict[i][6])
				}

		data = {
			"travelinfo": travelinfo,
			"destination": destination,
			"locations": locations
			}

		fname = QtGui.QFileDialog.getSaveFileName(self, filter = "Text files (*.txt)")
		try:
			f = open(fname, 'w')
			with f:
				json.dump(data, f, sort_keys = True, indent = 4)
			f.close()
		except IOError:
			pass

	def btn_getdist(self):
		"""Starts a thread that gets distances from relevant data"""
		x = threading.Thread(target = self.getdist)
		x.setDaemon(True)
		x.start()

	def getdist(self):
		"""Gets JSON object from Google matrix API"""
		self.ttdaemon.saveUpdate(False)

		datadict = self.selectTab()

		for i in datadict.keys():
			del datadict[i][5:]
		self.ttdaemon.tableUpdate()

		self.google.addMode(self.gsType.currentText())
		queriedDestinations = self.selectData()

		"""Breaks destinations down into chunks of 1 origin, DESTLIMIT destinations"""
		if queriedDestinations == []:
			pass
		else:
			DESTLIMIT = 99
			loops = len(queriedDestinations) / DESTLIMIT
			if (len(queriedDestinations) % DESTLIMIT) > 0:
				loops += 1
			data = []

			timesround = 0
			self.ttdaemon.progressUpdate(loops, timesround)
			for i in range(loops):
				start = i * DESTLIMIT
				finish = start + DESTLIMIT
				if finish > len(queriedDestinations):
					finish = start + (len(queriedDestinations) % DESTLIMIT)
				currentloop = queriedDestinations[start:finish]

				self.google.addOrigin(self.destLat.text(), self.destLon.text())
				for x in currentloop:
					self.google.addDestination(datadict[x][2], datadict[x][3])

				data.append(self.google.sendURL())
				time.sleep(10)
				timesround += 1
				self.ttdaemon.progressUpdate(loops, timesround)

			"""Takes JSON data and adds it to hotel dictionary"""
			for x in data:
				for i in x["rows"][0]["elements"]:
					try:
						distance = i["distance"]["text"]
						distance += "les"
					except KeyError:
						distance = "Error"
					try:
						duration = i["duration"]["text"]
					except KeyError:
						duration = "Error"
					location = queriedDestinations.pop(0)
					datadict[location].append(distance)
					datadict[location].append(duration)

		self.ttdaemon.tableUpdate()
		self.ttdaemon.saveUpdate(True)

	def tableChecks(self, row, col):
		"""Called by checkboxes being altered, changes the city selected"""
		city = ""
		name = ""
		ischecked = False
		checks = 0
		hotincity = 0

		datadict = self.selectTab()
		listview = ""
		if datadict == self.tt.tt_prochotels:
			listview = self.listHotels
		elif datadict == self.tt.tt_proctheatres:
			listview = self.listTheatres

		try:
			city = listview.item(row, 4).text()
			name = listview.item(row, 1).text()
			ischecked = listview.item(row, col).checkState()
			for i in range(self.listHotels.rowCount()):
				if listview.item(i, 0).checkState():
					checks += 1
				if listview.item(i, 4).text() == city:
					hotincity += 1
		except AttributeError:
			pass

		if ischecked:
			if city != "":
				self.checkeditems[name] = city

			onecity = []
			for i in self.checkeditems.keys():
				if self.checkeditems[i] not in onecity:
					onecity.append(self.checkeditems[i])
			if len(onecity) > 1 or checks != hotincity:
				currentindex = self.destCity.findText("Checked items")
				self.destCity.setCurrentIndex(currentindex)
			else:
				currentindex = self.destCity.findText(city)
				self.destCity.setCurrentIndex(currentindex)
		else:
			if name in self.checkeditems.keys():
				del self.checkeditems[name]
			if checks != hotincity:
				currentindex = self.destCity.findText("Checked items")
				self.destCity.setCurrentIndex(currentindex)

	def comboChecks(self, cityindex):
		"""Called by city combo box being altered, changes selected hotels"""
		combocity = self.destCity.itemText(cityindex)

		datadict = self.selectTab()
		listview = ""
		if datadict == self.tt.tt_prochotels:
			listview = self.listHotels
		elif datadict == self.tt.tt_proctheatres:
			listview = self.listTheatres

		for i in range(listview.rowCount()):
			city = listview.item(i, 4).text()
			name = listview.item(i, 1).text()
			if city == combocity:
				if name not in self.checkeditems.keys():
					self.checkeditems[name] = city
				listview.item(i, 0).setCheckState(QtCore.Qt.Checked)
			else:
				listview.item(i, 0).setCheckState(QtCore.Qt.Unchecked)
				if name in self.checkeditems.keys():
					del self.checkeditems[name]

	def tabChecks(self, tab):
		"""Called by tab change, unchecks all boxes in that tab"""
		if tab == 1:
			"""Theatres selected"""
			for i in self.checkeditems.keys():
				del self.checkeditems[i]
			for i in range(self.listHotels.rowCount()):
				self.listHotels.item(i, 0).setCheckState(QtCore.Qt.Unchecked)
		elif tab == 0:
			"""Hotels selected"""
			for i in self.checkeditems.keys():
				del self.checkeditems[i]
			for i in range(self.listTheatres.rowCount()):
				self.listTheatres.item(i, 0).setCheckState(QtCore.Qt.Unchecked)

	@QtCore.pyqtSlot()
	def tableUpdate(self):
		"""Updates table with latest version of hotel and theatre dictionary"""
		for index, hotelinfo in enumerate(self.tt.tt_prochotels.keys()):
			for index2, hotelitem in enumerate(self.tt.tt_prochotels[hotelinfo]):
				row = index
				col = index2
				if self.listHotels.rowCount() < len(self.tt.tt_prochotels.keys()):
					self.listHotels.insertRow(self.listHotels.rowCount())
				if hotelitem != None:
					if isinstance(hotelitem, QtGui.QTableWidgetItem):
						if isinstance(self.listHotels.item(row, col), QtGui.QTableWidgetItem):
							pass
						else:
							self.listHotels.setItem(row, col, hotelitem)
					else:
						self.listHotels.setItem(row, col, QtGui.QTableWidgetItem(hotelitem))
				else:
					self.listHotels.setItem(row, col, QtGui.QTableWidgetItem(""))

		self.listHotels.resizeColumnsToContents()

		for index, theatreinfo in enumerate(self.tt.tt_proctheatres.keys()):
			for index2, theatreitem in enumerate(self.tt.tt_proctheatres[theatreinfo]):
				row = index
				col = index2
				if self.listTheatres.rowCount() < len(self.tt.tt_proctheatres.keys()):
					self.listTheatres.insertRow(self.listTheatres.rowCount())
				if theatreitem != None:
					if isinstance(theatreitem, QtGui.QTableWidgetItem):
						if isinstance(self.listTheatres.item(row, col), QtGui.QTableWidgetItem):
							pass
						else:
							self.listTheatres.setItem(row, col, theatreitem)
					else:
						self.listTheatres.setItem(row, col, QtGui.QTableWidgetItem(theatreitem))
				else:
					self.listTheatres.setItem(row, col, QtGui.QTableWidgetItem(""))

		self.listTheatres.resizeColumnsToContents()

	@QtCore.pyqtSlot()
	def cityUpdate(self):
		"""Updates city combobox with list of all cities from loaded hotels and theatres, makes buttons available"""
		for i in range(self.listHotels.rowCount()):
			if self.listHotels.item(i, 4) != None:
				loc = self.listHotels.item(i, 4).text()
				if loc not in self.cities:
					self.cities.append(loc)
					self.destCity.clear()
					self.destCity.insertItems(0, self.cities)

		self.gsGet.setEnabled(True)

	@QtCore.pyqtSlot(int, int)
	def progressUpdate(self, total, current):
		"""Updates the progress bar for the menu"""
		self.conProgress.setMaximum(total)
		self.conProgress.setValue(current)

	@QtCore.pyqtSlot(bool)
	def saveUpdate(self, yn):
		"""Updates the save distances button"""
		if yn == True:
			self.gsSave.setEnabled(True)
		else:
			self.gsSave.setEnabled(False)



class TTDaemon(QtCore.QObject):
	"""The daemon thread in the UI that updates stuff on the fly"""
	table = QtCore.pyqtSignal()
	city = QtCore.pyqtSignal()
	progress = QtCore.pyqtSignal(int, int)
	save = QtCore.pyqtSignal(bool)

	def __init__(self):
		QtCore.QObject.__init__(self)

	def tableUpdate(self):
		self.table.emit()

	def cityUpdate(self):
		self.city.emit()

	def progressUpdate(self, total, current):
		self.progress.emit(total, current)

	def saveUpdate(self, yn):
		self.save.emit(yn)



class TTComms(object):
	"""Handles all communication with TT server via suds"""
	def __init__(self, username, password):
		self.username = str(username)
		self.password = str(password)
		self.tt = Client("http://www.tickettree.com/service/ttservice.asmx?wsdl")
		self.tt_rawhotels = self.tt.service.GetAllHotels(self.username, self.password)
		self.tt_prochotels = {}
		self.tt_rawshows = self.tt.service.GetAllShows(self.username, self.password)
		self.tt_procshows = []
		self.tt_proctheatres = {}

		self.gethotels()
		self.getshows()

		"""Prepares suds threadsafe queue"""

		self.MAX_THREADS = 10
		self.suds_service_queue = Queue(self.MAX_THREADS)
		for n in range(self.MAX_THREADS):
			self.suds_service_queue.put(Client("http://www.tickettree.com/service/ttservice.asmx?wsdl"))

	def getll_theatre(self, show):
		"""Retrieves the theatre associated with a particular show"""
		with self.get_suds_client() as client:
			theatreinfo = client.service.getTheatreInfo(self.username, self.password, show)
			theatrename = theatreinfo[0].rstrip()
			theatrecity = theatreinfo[3].rstrip()
			theatrelat = theatreinfo[8].rstrip()
			theatrelon = theatreinfo[7].rstrip()

			box = QtGui.QTableWidgetItem()
			box.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
			box.setCheckState(QtCore.Qt.Unchecked)

			if theatrename not in self.tt_proctheatres.keys():
				self.tt_proctheatres[theatrename] = [box, theatrename, theatrelat, theatrelon, theatrecity]

	def getshows(self):
		"""Gets a list of all shows, active or not"""
		for i in self.tt_rawshows[1][0][0][0][0]:
			self.tt_procshows.append(i[3][0])

	def gethotels(self):
		"""Loads tt_prochotels as ID: [hotelname]"""
		for hotelitem in self.tt_rawhotels[0]:
			box = QtGui.QTableWidgetItem()
			box.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
			box.setCheckState(QtCore.Qt.Unchecked)
			self.tt_prochotels[hotelitem[0]] = [box, hotelitem[1]]
			# [0] is ID, [1] is hotel name

	@contextmanager
	def get_suds_client(self):
		"""Suds threadsafe workaround, used on hotel requests"""
		"""From http://idbentley.com/blog/2014/09/16/using-python-suds-in-a-multi-thread-slash-multi-process-environment/"""
		client = self.suds_service_queue.get() # blocks until client available
		try:
			yield client
		finally:
			self.suds_service_queue.put(client)

	def getll(self, hotelID):
		"""Takes a hotel ID and adds the lattitude and longitude to the ID's dict entry"""
		with self.get_suds_client() as client:
			hotelinfo = client.service.getHotelInfo(self.username, self.password, self.tt_prochotels[hotelID][1])
			if hotelinfo[11] == None or hotelinfo[12] == None:
				self.tt_prochotels[hotelID].append(0)
				self.tt_prochotels[hotelID].append(0)
				self.tt_prochotels[hotelID].append(0)
			else:
				self.tt_prochotels[hotelID].append(hotelinfo[11])
				self.tt_prochotels[hotelID].append(hotelinfo[12])
				self.tt_prochotels[hotelID].append(hotelinfo[3].rstrip())

	def getll_handler(self, threads):
		"""Adds threaded suds queries onto a list given to the function, then runs them"""
		del threads[:]
		
		for i in self.tt_prochotels.keys():
			if len(self.tt_prochotels[i]) > 1:
				del self.tt_prochotels[i][2:]
			threads.append(threading.Thread(target = self.getll, args = (i, )))

		for i in self.tt_procshows:
			threads.append(threading.Thread(target = self.getll_theatre, args = (i, )))

		for i in threads:
			i.setDaemon(True)



class GoogleComs(object):
	"""Talks to Google, arranges URLs"""
	def __init__(self, key):
		"""Handles communication with Google's API"""
		self.key = "key=" + str(key)
		self.google = "https://maps.googleapis.com/maps/api/distancematrix/json?"
		self.mode = "mode=walking"
		self.units = "units=imperial"

		self.urltosend = ""

		# remember to stick & between parameters

	def addMode(self, mode):
		if mode == "Walking":
			self.mode = "mode=walking"
		if mode == "Public transport":
			self.mode = "mode=transit"
		if mode == "Car":
			self.mode = "mode=driving"
		if mode == "Bicycle":
			self.mode = "mode=bicycling"

	def addOrigin(self, lat, lon):
		"""Adds an origin to self.urltosend"""
		self.urltosend = self.google + "origins=" + lat + "," + lon + "&destinations="

	def addDestination(self, lat, lon):
		"""Adds a destination to the self.urltosend"""
		self.urltosend += str(lat) + "," + str(lon) + "|"

	def sendURL(self):
		"""Fires URL at Google"""
		self.urltosend += "&" + self.mode + "&" + self.units
		if self.key != "key=":
			self.urltosend += "&" + self.key
		response = urllib2.urlopen(str(self.urltosend))
		self.urltosend = ""
		data = json.loads(response.read())
		return data


if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	intro = IntroUI()
	intro.rejected.connect(intro.quit)
	intro.exec_()
	if intro.cancel == False:
		myapp = TTUI(intro.info)
		myapp.show()
		myapp.onLoad_wrapper()
		sys.exit(app.exec_())