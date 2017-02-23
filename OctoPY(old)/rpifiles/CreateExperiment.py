#!/usr/bin/env python

import io
import argparse
import os


def main(args) :
	folder = args.experiment
	configFile = "config_" + args.experiment + ".cfg"
	classFile = "Simulation" + args.experiment
	mainClass = classFile

	if not os.path.isdir(folder) :
		# Creation of the configuration file
		print("Creating configuration file " + configFile + "...")
		with open(configFile, "w") as fileOut :
			codeFile = """# Class name of the simulation
simulation_name = """ + mainClass + """

# Path of simulation
simulation_path = """ + folder + """.""" + classFile

			fileOut.write(codeFile)

		# Creation of the experiment folder
		print("Creating folder " + folder + "...")
		os.mkdir(folder)

		# Creation of the __init__.py file
		print("Creating __init__.py file...")
		os.mknod(os.path.join(folder, "__init__.py"))

		# Creation of the Simulation file
		print("Creating simulation file " + classFile + "...")
		with open(os.path.join(folder, classFile + ".py"), "w") as fileOut :
			codeFile = """#!/usr/bin/env/python

import Simulation
import Params

class """ + mainClass + """(Simulation.Simulation) :
	def __init__(self, controller, mainLogger) :
		Simulation.Simulation.__init__(self, controller, mainLogger)

	def preActions(self) :
		pass

	def postActions(self) :
		pass

	def step(self) :
		pass"""

			fileOut.write(codeFile)
	else :
		print("Experiment folder " + folder + " exists already !")


if __name__ == "__main__" :
	parser = argparse.ArgumentParser()
	parser.add_argument('experiment', help = "Name of the experiment.")
	args = parser.parse_args()

	main(args)