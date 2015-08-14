#!/usr/bin/env python

import os
import sys
import logging
import traceback
import threading
import socket
import argparse
import glib, gobject
import dbus, dbus.mainloop.glib
import time
import importlib
import subprocess

from utils import recvall, recvOneMessage, sendOneMessage, MessageType
import Params
import Simulation



CURRENT_FILE_PATH = os.path.abspath(os.path.dirname(__file__))

LOG_PATH = os.path.join(CURRENT_FILE_PATH, 'log', 'MainController.log')

# DEFAULT_SIMULATION_CFG = os.path.join(CURRENT_FILE_PATH, 'default_simulation.cfg')
# DEFAULT_SIMULATION_CFG = os.path.join(CURRENT_FILE_PATH, 'braitenberg.cfg')
# DEFAULT_SIMULATION_CFG = os.path.join(CURRENT_FILE_PATH, 'simulationMusic.cfg')
DEFAULT_SIMULATION_CFG = os.path.join(CURRENT_FILE_PATH, 'detectColor.cfg')

COMMANDS_LISTENER_HOST = ''
COMMANDS_LISTENER_PORT = 55555
TRUSTED_CLIENTS = ['192.168.0.210']


global mainLogger
mainLogger = None

# Messages from CommandsListener
class MessageCommand() :
	NONE = -1
	START, PAUSE, RESTART,STOP, KILL, SET = range(0, 6)


# Simulation observer
class Observer() :
	def __init__(self, IP, ID) :
		self.__IP = IP
		self.__ID = ID	

	def notify(self, **params) :
		message = utils.Message()
		message.msgType = MessageType.NOTIFY

		params['receiver'] = self.__ID

		# We send the notification message
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((self.__IP, 55555))
		sendOneMessage(sock, message)


	def getID(self) :
		return self.__ID

	IP = property(getID)

	def getIP(self) :
		return self.__IP

	IP = property(getIP)

class MainController() :
	def __init__(self) :
		self.__simulation = None
		self.__simulationConfig = None

		self.__cmdListener = CommandsListener(self)

		self.__commandReceived = threading.Condition()
		self.__command = MessageCommand.NONE
		self.__commandData = None

		self.__observers = []


	def __startSimulation(self) :
		if self.__simulation and not self.__simulation.isStopped() :
			mainLogger.error('MainController - Request for simulation start while a simulation is already running.')
		else :
			if not self.__simulation :
				if not self.__simulationConfig :
					mainLogger.info('MainController - No simulation configuration file loaded. Loading default simulation ' + DEFAULT_SIMULATION_CFG)
					self.__simulationConfig = DEFAULT_SIMULATION_CFG

				self.__loadSimulation()
			else :
				self.__simulation.reset()

			mainLogger.info('MainController - Starting simulation')
			self.__simulation.start()

	def __pauseSimulation(self) :
		if not self.__simulation or self.__simulation.isStopped() :
			mainLogger.error('MainController - Request for simulation pause while no simulation started.')
		else :
			mainLogger.info('MainController - Pausing simulation')
			self.__simulation.pause()

	def __restartSimulation(self) :
		if not self.__simulation or self.__simulation.isStopped() :
			mainLogger.error('MainController - Request for simulation restart while no simulation started.')
		elif self.__simulation and not self.__simulation.isPaused() :
			mainLogger.error('MainController - Request for simulation restart while no simulation paused.')
		else :
			mainLogger.info('MainController - Restarting simulation')
			self.__simulation.restart()

	def __setSimulation(self, configFile) :
		if os.path.isfile(os.path.join(CURRENT_FILE_PATH, configFile)) :
			self.__simulationConfig = os.path.join(CURRENT_FILE_PATH, configFile)
		else :
			mainLogger.error('MainController - No configuration file named ' + configFile)

	def __stopSimulation(self) :
		if not self.__simulation or self.__simulation.isStopped() :
			mainLogger.error('MainController - Request for simulation stop while no simulation started.')
		else :
			mainLogger.info('MainController - Stopping simulation')
			self.__simulation.stop()

	def __loadSimulation(self) :
		mainLogger.debug('MainController - Loading simulation...')
		Params.params = Params.Params(self.__simulationConfig, mainLogger)

		# We check for the basic parameters
		if Simulation.Simulation.checkForCompParams() :
			simModule = importlib.import_module(Params.params.simulation_path)
			simClass = getattr(simModule, Params.params.simulation_name)
			self.__simulation = simClass(self, mainLogger)
		else :
			mainLogger.error('MainController - Couldn\'t load simulation, compulsory parameter missing.')

	def __killController(self) :
		mainLogger.debug("MainController - Killing controller.")
		if self.__simulation and not self.__simulation.isStopped() :
			mainLogger.debug("MainController - Killing simulation.")
			self.__simulation.stop()

		mainLogger.debug("MainController - Killing asebamedulla.")
		proc = subprocess.Popen(["sh", "./killAseba.sh"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		(out, err) = proc.communicate()

		mainLogger.debug(str(out) + "/" + str(err))


	def register(self, data) :
		if "IP" not in data :
			mainLogger.error("MainController - No IP for registering observer.")
			return False

		if "ID" not in data :
			mainLogger.error("MainController - No ID for registering observer.")
			return False

		observerIP = data["IP"]
		observerID = data["ID"]

		for observer in self.__observers :
			if observer.ID == observerID :
				mainLogger.error("MainController - Trying to add observer already registered : " + str(observerID))
				return False

		self.__observers.append(Observer(observerIP, observerID))

	def notify(self, **params) :
		for observer in self.__observers :
			observer.notify(**params)


	def getCommand(self, command, data = None) :
		mainLogger.debug("MainController - Command " + str(command) + " received.")
		with self.__commandReceived :
			self.__command = command
			self.__commandData = data
			self.__commandReceived.notify()


	def run(self) :
		mainLogger.debug("MainController - Running.")

		# Start listening to commands
		self.__cmdListener.start()

		while 1 :
			try :
				with self.__commandReceived :
					# The controller waits for a command
					while self.__command == MessageCommand.NONE :
						self.__commandReceived.wait(1)

					# We treat the command corresponding to the message
					if self.__command == MessageCommand.START :
						self.__startSimulation()
					elif self.__command == MessageCommand.PAUSE :
						self.__pauseSimulation()
					elif self.__command == MessageCommand.RESTART :
						self.__restartSimulation()
					elif self.__command == MessageCommand.SET :
						self.__setSimulation(self.__commandData)
					elif self.__command == MessageCommand.STOP :
						self.__stopSimulation()
					elif self.__command == MessageCommand.KILL :
						self.__killController()
						break
					elif self.__comand == MessageCommand.REGISTER :
						self.__register(self.__commandData)

					self.__command = MessageCommand.NONE
			except KeyboardInterrupt :
				self.__killController()
				break
			except :
				mainLogger.critical('MainController - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc())

		mainLogger.debug("MainController - Exiting")



class CommandsListener(threading.Thread) :
	def __init__(self, controller) :
		threading.Thread.__init__(self)

		self.__controller = controller

		# We set daemon to True so that CommandsListener exits when the main thread is killed
		self.daemon = True

		# Create socket for listening to simulation commands
		self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.__sock.bind((COMMANDS_LISTENER_HOST, COMMANDS_LISTENER_PORT))
		self.__sock.listen(5)

	def run(self):
		while 1:
			try:
				# Waiting for client...
				mainLogger.debug("CommandsListener - Waiting on accept...")
				conn, (addr, port) = self.__sock.accept()

				mainLogger.debug('CommandsListener - Received command from (' + addr + ', ' + str(port) + ')')
				if addr not in TRUSTED_CLIENTS:
					mainLogger.error('CommandsListener - Received connection request from untrusted client (' + addr + ', ' + str(port) + ')')
					continue
				
				# Receive one message
				mainLogger.debug('CommandsListener - Receiving command...')
				message = recvOneMessage(conn)
				mainLogger.debug('CommandsListener - Received ' + str(message))

				# The listener transmits the desired command
				messageCommand = MessageCommand.NONE
				data = None
				if message.msgType == MessageType.START :
					messageCommand = MessageCommand.START
				elif message.msgType == MessageType.PAUSE :
					messageCommand = MessageCommand.PAUSE
				elif message.msgType == MessageType.RESTART :
					messageCommand = MessageCommand.RESTART
				elif message.msgType == MessageType.SET :
					messageCommand = MessageCommand.SET
					data = message.data
				elif message.msgType == MessageType.STOP :
					messageCommand = MessageCommand.STOP
				elif message.msgType == MessageType.KILL :
					messageCommand = MessageCommand.KILL
				elif message.msgType == MessageType.REGISTER :
					messageCommand = MessageCommand.REGISTER

					# We add the IP of the observer
					data["IP"] = addr
					data = message.data

				mainLogger.debug('CommandsListener - Transmitting command ' + str(messageCommand)+ ' to controller.')
				self.__controller.getCommand(messageCommand, data)
			except:
				mainLogger.critical('CommandsListener - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc())

		mainLogger.debug('CommandsListener - Exiting...')


if __name__ == '__main__' :
	parser = argparse.ArgumentParser()
	parser.add_argument('-L', '--log', default = True, action = "store_true", help = "Log messages in a file")
	parser.add_argument('-d', '--debug', default = True, action = "store_true", help = "Debug mode")
	parser.add_argument('-i', '--hostIP', default = None, help = "Host IP address")
	args = parser.parse_args()

	# Creation of the logging handlers
	level = logging.INFO
	if args.debug :
		level = logging.DEBUG

	mainLogger = logging.getLogger()
	mainLogger.setLevel(level)

	# File Handler
	if args.log :
		fileHandler = logging.FileHandler(LOG_PATH)
		formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
		fileHandler.setFormatter(formatter)
		fileHandler.setLevel(level)
		mainLogger.addHandler(fileHandler)

	# Console Handler
	consoleHandler = logging.StreamHandler()
	consoleHandler.setLevel(level)
	mainLogger.addHandler(consoleHandler)

	try:
		# To avoid conflicts between gobject and python threads
		gobject.threads_init()
		dbus.mainloop.glib.threads_init()

		controller = MainController()
		controller.run()
	except:
		mainLogger.critical('Error in main: ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc())
