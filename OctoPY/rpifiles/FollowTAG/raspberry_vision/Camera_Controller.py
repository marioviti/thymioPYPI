import picamera
from picamera import PiCamera
from picamera.array import PiRGBArray
import threading
import cv2
import time
import settings

class Camera_Controller(threading.Thread):
    def __init__(self, camera_settings = settings.camera_settings):
        super(Camera_Controller, self).__init__()
        # load camera settings
        self.load_camera_settings(camera_settings)
        # initialize camera
        self.initialize_camera()
        # initialize image buffer
        self.initialize_image_buffer()
        # initialize lock
        self.initialize_locks()

    def shutdown(self):
        self.running = False

    def initialize_locks(self):
        self.processing_buffer_lock = threading.Lock()

    def load_camera_settings(self,camera_settings):
        self.resolution = camera_settings['resolution']
        self.framerate = camera_settings['framerate']
        self.frame_format = camera_settings['frame']['format']
        self.use_video_port = camera_settings['frame']['use_video_port']

    def initialize_camera(self):
        self.camera = PiCamera()
        # wait for camera to heat up sensors
        time.sleep(2)
        self.camera.resolution = self.resolution
        self.camera.framerate = self.framerate

    def initialize_image_buffer(self):
        self.image_buffer = PiRGBArray(self.camera)
        self.processing_buffer = None

    def run(self):
        # setting flag for gracious termination
        self.running = True
        for frame in self.camera.capture_continuous(self.image_buffer, \
            format=self.frame_format , use_video_port=self.use_video_port):
            if not self.running:
                break
            with self.processing_buffer_lock:
                #print "captured image"
                self.processing_buffer = frame.array.copy() # keep a copy
            self.image_buffer.seek(0)
            self.image_buffer.truncate()