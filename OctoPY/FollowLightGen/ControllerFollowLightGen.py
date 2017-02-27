#!/usr/bin/env/python
# -*- coding: utf-8 -*-

"""
P_ANDROIDE UPMC 2017
Encadrant : Nicolas Bredeche

@author Tanguy SOTO
@author Parham SHAMS

Controleur principal du comportement évolutionniste de suivi de lumière.
"""

import time

import Controller
import OctoPY
import Params

from utils import MessageType

MAX=8

class ControllerFollowLightGen(Controller.Controller) :
	def __init__(self, controller, mainLogger) :
		Controller.Controller.__init__(self, controller, mainLogger)
		self.stepp=0
		
	def preActions(self) :	
		
		if self.octoPYInstance.hashThymiosHostnames :
			self.log("Helloooo555")
			# Init all robots
			self.log("Send init...")
			self.octoPYInstance.sendMessage(MessageType.INIT, [])
			time.sleep(2)

			# Load simulation
			self.log("Load simulation...")
			self.octoPYInstance.sendMessage(MessageType.SET, [], "config_FollowLightGen.cfg")
			time.sleep(2)

			# Start simulation
			self.log("Start simulation...")
			self.octoPYInstance.sendMessage(MessageType.START, [])

	def postActions(self) :
		self.log("Stop simulation...")
		self.octoPYInstance.sendMessage(MessageType.STOP, [])
		time.sleep(1)

		# Kill controllers
		self.log("Kill controller...")
		#self.octoPYInstance.sendMessage(MessageType.KILL, [])
		
		self.log("ControllerFollowLightGen - postActions : Appel a self.stop")
		self.stop()

	def step(self) :
		self.stepp+=1
		time.sleep(1)
		self.log(self.stepp)
		if self.stepp>MAX:
			self.postActions()

	def notify(self, **arg) :
		pass
