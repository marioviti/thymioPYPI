import dbus
import dbus.mainloop.glib
import gobject
#import sys
import time
from ThymioFunctions import *
from optparse import OptionParser

def avoidingObstacles():

    for i in xrange(7):
	proxSensors[i]=getSensorValue(i)
    """
   Pour ameliorer    

    weight1=[1,2,3,2,1]
    weight2=[-4,-3,0,3,4]

    temp_braitenberg=0

    if acc[]>0: # thymio is moving forward
	temp_braitenberg=np.dot(weight1, proxSensors[0:5])
	temp_braitenberg/=16
	temp_braitenberg_turn=np.dot(weight2, proxSensors[0:5])
	temp_braitenberg_turn/=16
	temp_bratenberg_left=

	leftWheel=[0.01,0.05,-0.07,-0.05,-0.01, 0.03, 0.04]
	rightWheel=[-0.01,-0.05,-0.07,0.05,0.01,0.04, 0.03]

    """
	
    #Parameters of the Braitenberg, to give weight to each wheels 
    leftWheel=[0.01,0.05,-0.07,-0.05,-0.01, 0.03, 0.04]
    rightWheel=[-0.01,-0.05,-0.07,0.05,0.01,0.04, 0.03]

    #Braitenberg algorithm
    totalLeft=0
    totalRight=0
    for i in range(7):
         totalLeft=totalLeft+(proxSensors[i]*leftWheel[i])
         totalRight=totalRight+(proxSensors[i]*rightWheel[i])

    # add a constant speed to each wheels so the robot moves always forward
    totalRight=totalRight+100
    totalLeft=totalLeft+100

    # send motor value to the robot 
    setMotorSpeed(totalLeft, totalRight)
    if time.time()-start>=run_time:
	   setMotorSpeed(0, 0)
	   print time.time()-start
	   loop.quit()
	   return False

    return True


if __name__ == '__main__':

    start = time.time()
    run_time = 10
    parser = OptionParser()
    parser.add_option("-s", "--system", action="store_true", dest="system", default=False,help="use the system bus instead of the session bus")
 
    (options, args) = parser.parse_args()
 
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
 
    if options.system:
        bus = dbus.SystemBus()
    else:
        bus = dbus.SessionBus()
 
    #Create Aseba network 
    network = dbus.Interface(bus.get_object('ch.epfl.mobots.Aseba', '/'), dbus_interface='ch.epfl.mobots.AsebaNetwork')
 
    #print in the terminal the name of each Aseba NOde
    print network.GetNodesList()
 
    #GObject loop
    print 'starting loop'
    loop = gobject.MainLoop()
    #call the callback of Braitenberg algorithm
    handle = gobject.timeout_add (100, avoidingObstacles) #every 0.1 sec
    loop.run()
