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

import multiprocessing
from multiprocessing import Process, Queue, Value, Manager


#from facerecognizer import FaceRecognizer
from frame import Frame
from ohinterface import OHInterface
from face import Face
from presencedetector import PresenceDetector
import logging
from logging.config import fileConfig

class FrameWorker:
    def __init__(self):
        #pipeline to operate on 
        self.pipeline = Queue()
        self.faceReconizer = None #FaceRecognizer()
        self.thread = None
        self.process = None
        self.presenceDetector = None #TF not multiprocessing safe. call PresenceDetector() in process
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("FrameWorker")
        self.OHInterface = OHInterface()


        #mutliproc
        self.manager = multiprocessing.Manager()
        self.globalns = self.manager.Namespace()
        self.knownFaceList = self.manager.list()
        self.unknownFaceList = self.manager.list()
        self.globalns.workingFPS = 0
        self.globalns.lastFrame = None
        self.globalns.idle = True
        self.globalns.sessionPresence = False
        self.globalns.processedFrames = 0
        self.globalns.newPresence = False

    #----------getter/setter API-----------
    def getIdle(self):
        return self.globalns.idle

    def getFPS(self):
        return self.globalns.workingFPS

    def getProcessedFrames(self):
        return self.globalns.processedFrames

    def getKnownFromList(self, index):
        if len(self.knownFaceList)>0:            
            return self.knownFaceList[index]
        else:
            self.logger.error("No known face in list")
            return None

    def getLastKnown(self):
        return self.getKnownFromList(len(self.knownFaceList)-1)


    def getUnknownFromList(self, index):
        if len(self.unknownFaceList)>0:
            return self.unknownFaceList[index]
        else:
            self.logger.error("No unknown face in list")
            return None

    def getLastUnknown(self):
        return self.getUnknownFromList(len(self.unknownFaceList)-1)
    
    def getKnownCount(self):
        return len(self.knownFaceList)

    def getUnknownCount(self):
        return len(self.unknownFaceList)


    def getLastFrame(self):
        if not self.globalns.lastFrame == None:
            return self.globalns.lastFrame
        else:
            self.logger.error("Not implemented")       
    
    def alertUnknown(self):
        if self.getUnknownCount()> 0:
            self.OHInterface.unknownAlert(self.getUnknownCount())

    

    #----------Start and Process Mgmt---------
    def startNewSession(self,kfl,ufl,ns):
        #reset/delete all lists of known and unknoen faces.
        self.logger.info("Resetting Session - starting new")
        #empty lists (kfl=[] not working)
        del kfl[:]
        del ufl[:]
        ns.sessionPresence = False

    def start(self, pipe):
        self.pipeline = pipe
        
        self.logger.info("Setting up Sub-Process for Frameworker")

        self.process = Process(target=self.work, args=(pipe.Q, self.globalns, self.knownFaceList, self.unknownFaceList))
        self.process.daemon = True
        self.process.start()
        
        self.logger.info("FrameWorker started.")
        
        
    def work(self, frameQ, ns, kfl, ufl):
        from facerecognizer import FaceRecognizer

        #called in separate Thread to work on pipeline
        self.presenceDetector = PresenceDetector()
        self.faceReconizer = FaceRecognizer()
        while True:            
            
            if not frameQ.empty():#ret:
                frame = frameQ.get()
                
                ns.lastFrame=frame
                ns.processedFrames += 1                
                #self.logger.info("Got frame, start Face recognition.")
                #Session tracking via idle. Works only as long as streaming from cam is faster than frameworker!
                if ns.idle:
                    #new working session started
                    self.startNewSession(kfl,ufl,ns)  
                ns.idle=False                  

                #self.logger.info("Received Frame. Start Face Recognition. Timestamp: %s", time.ctime(frame.timestamp))
                startTime = time.time()
                self.faceReconizer.detectFaces(frame)                
                

                ns.newPresence = False
                self.presenceDetector.detectPresence(frame,kfl,ufl,ns)
                ns.workingFPS = 1/(time.time() - startTime)
                #self.logger.info("Frame Processed with FPS: %f. ", ns.workingFPS)

                if ns.newPresence:
                    #if new person detected. alert presence
                    self.OHInterface.setPresent(self.getLastKnown().name)                    
                
            else:
                #self.logger.info("No Frame on Queue. Sleeping")
                
                if not ns.idle:
                    self.logger.info("Ending session. Processed %d frames.", ns.processedFrames)
                    #just got out of working session
                    #send unknown notification
                    if not ns.sessionPresence:
                        self.alertUnknown()
                    #DO NOT delete unonwns and knons list here, otherwise gone for server
                ns.idle=True
                time.sleep(1) #important to sleep. otherwise locking battle on queue
                
                
           
            

