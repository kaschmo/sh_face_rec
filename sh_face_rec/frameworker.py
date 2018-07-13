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
    from multiprocessing import Process, Queue, Value

else:
    from threading import Thread
    if sys.version_info >= (3, 0):
        from queue import Queue
    else:
        from Queue import Queue


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
        self.newSession = True #indicate if new session on VideoQueue startet. 
        self.detectKnownThenStop = False #Flag. If one known is detected, working session stops.
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("FrameWorker")
        self.OHInterface = OHInterface()


        #mutliproc
        self.knownFaceList = Queue()
        self.unknownFaceList = Queue()
        self.workingFPS = Value('d', 0.0)
        self.lastFrame = Queue() #easiest to set as queue. but need getter/setter function because it can never be >1 entry
        self.idle = Value('i',1)
        self.presence = Value('i',1)

    #----------getter/setter API-----------
    def getQLength(self, q):
        mycopy = []
        while not q.empty:            
            elem = q.get(block=False)            
            mycopy.append(elem)

        for elem in mycopy:
            q.put(elem)
        return len(mycopy)

    def getQElement(self, q, el):
        mycopy = []
        while not q.empty:
            elem = q.get(block=False)
            mycopy.append(elem)
        for elem in mycopy:
            q.put(elem)
        return mycopy[el]

    def getKnownFromList(self, index):
        if not self.knownFaceList.empty():
            #return self.knownFaceList.queue[index]
            return self.getQElement(self.knownFaceList,index)
        else:
            #TODO Execption
            return None

    def getLastKnown(self):
        return self.getKnownFromList(self.getQLength(self.knownFaceList)-1)

    def getUnknownFromList(self, index):
        if not self.unknownFaceList.empty():
            #return self.unknownFaceList.queue[index]
            return self.getQElement(self.unknownFaceList,index)
        else:
            #TODO Execption
            return None

    def getLastUnknown(self):
        #return self.getUnknownFromList(len(self.unknownFaceList.queue)-1)
        return self.getUnknownFromList(self.getQLength(self.unknownFaceList)-1)
    
    def getKnownCount(self):
        #direct access to deque in Queue - not process save!
        #return len(self.knownFaceList.queue)
        return self.getQLength(self.knownFaceList)

    def getUnknownCount(self):
        #direct access to deque in Queue - not process save!
        #return len(self.unknownFaceList.queue)
        return self.getQLength(self.unknownFaceList)


    def setLastFrame(self,lf,frame):
        if not lf.empty():
            #emptyQueue
            lf.get()
        lf.put(frame)

    def getLastFrame(self):
        #assume that this is only called from master process. otherwise I need to always set self.lastFrame in Child processes too
        if not self.lastFrame.empty():
            lastframe=self.lastFrame.get()
            self.lastFrame.put(lastframe)
            return lastframe
        else:
            self.logger.error("Not implemented")
    
    def emptyQueue(self, q):
        while not q.empty():
            q.get()

    def alertUnknown(self):
        if self.getUnknownCount()> 0:
            self.OHInterface.unknownAlert(self.getUnknownCount())

    #----------Start and Process Mgmt---------
    def startNewSession(self,kfl,ufl,presence):
        #reset/delete all lists of known and unknoen faces.
        self.logger.info("Resetting Session")
    
        self.emptyQueue(kfl)
        self.emptyQueue(ufl)        
        presence.value = 0

    def start(self, pipe):
        self.pipeline = pipe
        if cf.getboolean('MULTIPROC'):
            #multiprocessing.set_start_method('spawn', force=True)

            self.logger.info("Setting up Sub-Process for streaming")

            self.process = Process(target=self.work, args=(pipe.Q, self.lastFrame, self.knownFaceList, self.unknownFaceList, self.idle, self.presence, self.workingFPS))
            self.process.daemon = True
            self.process.start()
        else: 
            #create new Thread
            self.logger.info("Setting up Thread for streaming")

            self.thread = Thread(target=self.work)
            self.thread.daemon = True
            self.thread.start()
        self.logger.info("FrameWorker started.")
        
        
    def work(self, frameQ, lastFrame, kfl, ufl, idle,presence,fps):
        from facerecognizer import FaceRecognizer

        #called in separate Thread to work on pipeline
        self.presenceDetector = PresenceDetector()
        self.faceReconizer = FaceRecognizer()
        while True:
            #self.logger.info("Pipeline Length: %d", pipe.qsize())

            #ret, frame = self.pipeline.getFrame()
            
            
            if not frameQ.empty():#ret:
                frame = frameQ.get()
                self.setLastFrame(lastFrame,frame) #store last frame in queue
                
                idle.value=0
                #self.logger.info("Got frame, start Face recognition.")
                if self.newSession:
                    #new working session started
                    self.logger.info("Starting new working session")
                    self.startNewSession(kfl,ufl,presence)                    
                    self.newSession = False

                self.logger.info("Received Frame. Start Face Recognition. Timestamp: %s", time.ctime(frame.timestamp))
                startTime = time.time()
                self.faceReconizer.detectFaces(frame)                
                fps.value = 1/(time.time() - startTime)
                self.logger.info("Frame Processed with FPS: %f. ", fps.value)
                self.presenceDetector.detectPresence(frame,kfl,ufl,presence)
                
                if presence.value:
                    self.OHInterface.setPresent(self.getLastKnown.name)                    


                #if presence is detected and detectKnownThenStop flag is true, break current worker session
                if presence.value and self.detectKnownThenStop:
                    self.logger.info("Presence set. Stop streaming. Flush videoQ")
                    #self.pipeline.stopAndFlush()     
                    #TODO need to setup pipe between video proceee and sthi    
                
            else:
                self.logger.info("No Frame on Queue. Sleeping")
                idle.value=1
                #if not self.newSession and not self.pipeline.isStreaming:
                    #self.logger.info("Ending working session. Cleaning Up.")
                    #just got out of working session
                    #self.newSession = True
                    #send unknown notification
                    #self.presenceDetector.alertUnknown()
                    #DO NOT delete unonwns and knons list here, otherwise gone for server
                time.sleep(1) #important to sleep. otherwise locking battle on queue
                
                
           
            

