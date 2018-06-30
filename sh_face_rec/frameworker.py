#Worker Class that works on Frame pipeline in separate thread 
# - executes face recognition functions
# - determines presence in frame
# - calls back Home Automation

import sys
import time
import dlib
import sys
import configparser
config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['FRAMEWORKER']
if cf.getboolean('MULTIPROC'):
    import multiprocessing
    from multiprocessing import Process, Queue

else:
    from threading import Thread
    if sys.version_info >= (3, 0):
        from queue import Queue
    else:
        from Queue import Queue


from facerecognizer import FaceRecognizer
from frame import Frame
from ohinterface import OHInterface
from face import Face
from presencedetector import PresenceDetector
import logging
from logging.config import fileConfig

class FrameWorker:
    def __init__(self):
        #pipeline to operate on 
        self.pipeline = None
        self.faceReconizer = FaceRecognizer()
        self.thread = None
        self.workingFPS = 0
        self.process = None
        self.presenceDetector = PresenceDetector()
        self.newSession = True #indicate if new session on Queue startet. #TODO multiproc threadsafe?
        self.detectKnownThenStop = False #Flag. If one known is detected, working session stops.
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("FrameWorker")
        self.lastFrame = None
        self.idle = True

    def start(self, pipe):
        self.pipeline = pipe
        if cf.getboolean('MULTIPROC'):
            self.logger.info("Setting up Sub-Process for streaming")

            self.process = Process(target=self.work)
            self.process.daemon = True
            self.process.start()
        else: 
            #create new Thread
            self.logger.info("Setting up Thread for streaming")

            self.thread = Thread(target=self.work)
            self.thread.daemon = True
            self.thread.start()
        self.logger.info("FrameWorker started.")
        
        
    def work(self):
        #called in separate Thread to work on pipeline
        while True:
            ret, frame = self.pipeline.getFrame()
            
            if ret:
                self.lastFrame = frame #store frame
                self.idle=False
                #self.logger.info("Got frame, start Face recognition.")
                if self.newSession:
                    #new working session started
                    self.logger.info("Starting new working session")
                    self.presenceDetector.newSession()                    
                    self.newSession = False

                #print("Got Frame and start Face Recognition. Timestamp {}".format(time.ctime(frame.timestamp)))
                startTime = time.time()
                self.faceReconizer.detectFaces(frame)                
                self.workingFPS = 1/(time.time() - startTime)
                self.logger.info("Frame Processed with FPS: %f. Queue: %d", self.workingFPS, self.pipeline.getLength())
                self.presenceDetector.detectPresence(frame)
                
                #if presence is detected and detectKnownThenStop flag is true, break current worker session
                if self.presenceDetector.presence and self.detectKnownThenStop:
                    self.pipeline.stopAndFlush()         
                
            else:
                self.logger.info("No Frame on Queue. Sleeping")
                self.idle=True
                if not self.newSession and not self.pipeline.isStreaming:
                    self.logger.info("Ending working session. Cleaning Up.")
                    #just got out of working session
                    self.newSession = True
                    #send unknown notification
                    self.presenceDetector.alertUnknown()
                    #DO NOT delete unonwns and knons list here, otherwise gone for server
                time.sleep(1) #important to sleep. otherwise locking battle on queue
                
                
           
            

