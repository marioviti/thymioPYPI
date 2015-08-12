#!/usr/bin/env/python

import picamera
import io
import sys
import traceback
import logging
from PIL import Image
import cv2
import numpy as np
import time
import re
import xml.dom.minidom
import os
import random

import Simulation
import Params

CURRENT_FILE_PATH = os.path.abspath(os.path.dirname(__file__))

class SimulationStagHunt(Simulation.Simulation) :
	def __init__(self, controller, mainLogger, debug = False) :
		Simulation.Simulation.__init__(self, controller, mainLogger, debug)

		self.__camera = picamera.PiCamera()
		self.__camera.resolution = (Params.params.size_x, Params.params.size_y)

		# Matrix for the weights from input neurons to hidden neurons
		self.__weightsItoH = None

		# Matrix for the weights from hidden neurons to output neurons
		self.__weightsHtoO = None


	def preActions(self) :
		self.loadWeights(Params.params.weights_path, Params.params.file_xml)


	def loadWeights(self, file, xmlFile) :
		if os.path.isfile(os.path.join(CURRENT_FILE_PATH, file)) :
			self.log("Loading weights file " + os.path.join(CURRENT_FILE_PATH, file), logging.DEBUG)

			listGenes = []
			if xmlFile == 1:
				DOMTree = xml.dom.minidom.parse(os.path.join(CURRENT_FILE_PATH, file))
				genome = DOMTree.documentElement

				x = genome.getElementsByTagName("x")[0]

				if x :
					best = x.getElementsByTagName("_best")[0]

					if best :
						px = best.getElementsByTagName("px")[0]

						if px :
							gen = px.getElementsByTagName("_gen")[0]

							if gen :
								data = gen.getElementsByTagName("_data")[0]

								listItems = data.getElementsByTagName("item")

								for item in listItems :
									listGenes.append(float(item.childNodes[0].data))
			else :
				regexp = re.compile(r"^(\d+(\.\d+)?)$")
				with open(os.path.join(CURRENT_FILE_PATH, file), 'r') as fileWeights :
					fileWeights = fileWeights.readlines()

					for line in fileWeights :
						s = regexp.search(line)

						if s :
							gene = float(s.group(1))
							listGenes.append(gene)


			cptColumns = 0
			cptLines = 0
			self.__weightsItoH = np.zeros((Params.params.nb_inputs + 1, Params.params.nb_hidden))
			self.__weightsHtoO = np.zeros((Params.params.nb_hidden + 1, Params.params.nb_outputs))

			for gene in listGenes :
				# Genotype to weights : [0, 1] -> [min_weight, max_weight]
				weight = gene * (float)(Params.params.max_weight - Params.params.min_weight) + Params.params.min_weight

				if cptColumns < Params.params.nb_hidden :
					# We fill the first matrix
					self.__weightsItoH[cptLines, cptColumns] = weight

					cptLines += 1
					if cptLines >= Params.params.nb_inputs + 1 :
						cptLines = 0
						cptColumns += 1
				else :
					# We fill the second matrix
					self.__weightsHtoO[cptLines, cptColumns - (Params.params.nb_hidden)] = weight

					cptLines += 1
					if cptLines >= Params.params.nb_hidden + 1 :
						cptLines = 0
						cptColumns += 1
		else :
			self.log("Weights file " + file + " does not exist.")



	def postActions(self) :
		self.tController.writeMotorsSpeedRequest([0, 0])
		self.waitForControllerResponse()


	def getInputs(self) :
		inputs = np.zeros((1, Params.params.nb_inputs + 1))

		cpt = 0
		while cpt < Params.params.nb_inputs :
			inputs[0, cpt] = random.random()
			cpt += 1

		# inputs = self.getProximityInputs(inputs)

		# inputs = self.getCameraInputs(inputs)

		# Bias neuron
		inputs[0, -1] = 1.0

		return inputs

	def getProximityInputs(self, inputs) :
		try :
			self.tController.readSensorsRequest()
			self.waitForControllerResponse()
			PSValues = self.tController.getPSValues()

			for i in range(0, len(PSValues)) :
				inputs[0, i] = PSValues[i]
		except :
			self.log('SimulationStagHunt - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc(), logging.CRITICAL)
		finally :
			return inputs

	def getCameraInputs(self, inputs) :
		stream = io.BytesIO()

		# Capture into stream
		self.__camera.capture(stream, 'jpeg', use_video_port = True)
		data = np.fromstring(stream.getvalue(), dtype = np.uint8)
		img = cv2.imdecode(data, 1)

		# Blurring and converting to HSV values
		image = cv2.GaussianBlur(img, (5, 5), 0)
		image_HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
		
		# Locate the color
		mask = cv2.inRange(image_HSV, np.array([40, 40, 40]), np.array([80, 255, 255]))
		mask = cv2.GaussianBlur(mask, (5, 5), 0)
		
		# We get a list of the outlines of the white shapes in the mask
		contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

		# If we have at least one contour, we look through each one and pick the biggest
		if len(contours) > 0 :
			largest = 0
			area = 0

			for i in range(len(contours)) :
				# Get the area of the ith contour
				temp_area = cv2.contourArea(contours[i])

				# If it is the biggest we have seen, keep it
				if temp_area > area :
					area = temp_area
					largest = i

			# Compute the coordinates of the center of the largest contour
			coordinates = cv2.moments(contours[largest])
			targetX = int(coordinates['m10']/coordinates['m00'])
			targetY = int(coordinates['m01']/coordinates['m00'])

		return inputs

	def computeNN(self, inputs) :
		outputs = [-1.0, -1.0]

		try :
			def sigmoid(x) : return 1.0 / (1.0 + np.exp(-Params.params.lambda_sigmoid * x))

			# First computation : inputs to hidden
			hiddenNN = np.dot(inputs, self.__weightsItoH)
			hiddenNN = np.matrix(map(sigmoid, hiddenNN)).copy()

			# Second computation : hidden to outputs
			# Bias neuron
			hiddenNN.resize((1, Params.params.nb_hidden + 1))
			hiddenNN[0, -1] = 1.0

			outputsNN = np.dot(hiddenNN, self.__weightsHtoO)

			for i in range(0, Params.params.nb_outputs) :
				outputs[i] = sigmoid(outputsNN[0, i])

		except :
			self.log('SimulationStagHunt - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc(), logging.CRITICAL)
		finally :
			return outputs

	def step(self) :
		try :
			inputs = self.getInputs()
			outputs = self.computeNN(inputs)

			if (outputs[0] >= 0) and (outputs[1] >= 0) :
				self.tController.writeMotorsSpeedRequest([outputs[0] * Params.params.max_speed, outputs[1] * Params.params.max_speed])
				self.waitForControllerResponse()
			else :
				self.tController.writeMotorsSpeedRequest([0.0, 0.0])
				self.waitForControllerResponse

			time.sleep(Params.params.time_step/1000.0)
		except :
			self.log('SimulationStagHunt - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc(), logging.CRITICAL)


if __name__ == "__main__" :
	# Creation of the logging handlers
	level = logging.DEBUG

	mainLogger = logging.getLogger()
	mainLogger.setLevel(level)

	# File Handler
	fileHandler = logging.FileHandler(os.path.join(CURRENT_FILE_PATH, 'log', 'MainController.log'))
	formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
	fileHandler.setFormatter(formatter)
	fileHandler.setLevel(level)
	mainLogger.addHandler(fileHandler)

	# Console Handler
	consoleHandler = logging.StreamHandler()
	consoleHandler.setLevel(level)
	mainLogger.addHandler(consoleHandler)

	simu = SimulationStagHunt(None, mainLogger, True)
	simu.start()