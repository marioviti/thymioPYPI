import time
import random

import Params
import Simulation

class SimulationDefault(Simulation.Simulation) :
	def __init__(self, controller, mainLogger) :
		Simulation.Simulation.__init__(self, controller, mainLogger)

	def preActions(self) :
		pass

	def postActions(self) :
		self.waitForControllerResponse()
		self.tController.writeColorRequest([32, 32, 32])
		self.waitForControllerResponse()

	def Braitenberg(self, proxSensors):
	    #Parameters of the Braitenberg, to give weight to each wheels
	    leftWheel=[-0.01,-0.005,-0.0001,0.006,0.015]
	    rightWheel=[0.012,+0.007,-0.0002,-0.0055,-0.011]
	 
	    #Braitenberg algorithm
	    totalLeft=0
	    totalRight=0
	    for i in range(5):
	         totalLeft=totalLeft+(proxSensors[i]*leftWheel[i])
	         totalRight=totalRight+(proxSensors[i]*rightWheel[i])
	 
	    #add a constant speed to each wheels so the robot moves always forward
	    totalRight=totalRight+50
	    totalLeft=totalLeft+50

	    self.tController.writeMotorsSpeedRequest([totalLeft, totalRight])
	 
	    return True

	def step(self) :
		try :
			self.waitForControllerResponse()

			self.tController.readSensorsRequest()
			self.waitForControllerResponse()
			PSValues = self.tController.getPSValues()

			self.Braitenberg(PSValues)			
		except :
			self.mainLogger.critical('SimulationDefault - Unexpected error : ' + str(sys.exc_info()[0]) + ' - ' + traceback.format_exc())

