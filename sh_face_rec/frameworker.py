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
    from multiprocessing import Process, Queue, Value, Manager

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
        self.manager = multiprocessing.Manager()
        self.globalns = self.manager.Namespace()
        self.knownFaceList = self.manager.list()
        self.unknownFaceList = self.manager.list()
        self.globalns.workingFPS = 0
        self.globalns.lastFrame = None
        self.globalns.idle = True
        self.globalns.presence = False
        self.globalns.processedFrames = 0

    #----------getter/setter API-----------
    def getIdle(self):
        return self.globalns.idle

    def getFPS(self):
        return self.globalns.workingFPS

    def getProcessedFrames(self):
        return self.globalns.processedFrames

    def getKnownFromList(self, index):
        if len(self.knownFaceList)>0:
            #return self.knownFaceList.queue[index]
            #return self.getQElement(self.knownFaceList,index)
            return self.knownFaceList[index]
        else:
            #TODO Execption
            return None

    def getLastKnown(self):
        #return self.getKnownFromList(self.getQLength(self.knownFaceList)-1)
        return self.getKnownFromList(len(self.knownFaceList)-1)


    def getUnknownFromList(self, index):
        if len(self.unknownFaceList)>0:
            #return self.unknownFaceList.queue[index]
            #return self.getQElement(self.unknownFaceList,index)
            return self.unknownFaceList[index]
        else:
            #TODO Execption
            return None

    def getLastUnknown(self):
        #return self.getUnknownFromList(len(self.unknownFaceList.queue)-1)
        return self.getUnknownFromList(len(self.unknownFaceList)-1)
    
    def getKnownCount(self):
        #direct access to deque in Queue - not process save!
        #return len(self.knownFaceList.queue)
        return len(self.knownFaceList)

    def getUnknownCount(self):
        #direct access to deque in Queue - not process save!
        #return len(self.unknownFaceList.queue)
        return len(self.unknownFaceList)


    def getLastFrame(self):
        #assume that this is only called from master process. otherwise I need to always set self.lastFrame in Child processes too
        #if not self.lastFrame.empty():
        #    lastframe=self.lastFrame.get()
        #    self.lastFrame.put(lastframe)
        #    return lastframe
        #else:
        #    self.logger.error("Not implemented")
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
        self.logger.info("Resetting Session")
        kfl=[]
        ufl=[]
          
        ns.presence = False

    def start(self, pipe):
        self.pipeline = pipe
        if cf.getboolean('MULTIPROC'):
            #multiprocessing.set_start_method('spawn', force=True)

            self.logger.info("Setting up Sub-Process for streaming")

            self.process = Process(target=self.work, args=(pipe.Q, self.globalns, self.knownFaceList, self.unknownFaceList))
            self.process.daemon = True
            self.process.start()
        else: 
            #create new Thread
            self.logger.info("Setting up Thread for streaming")

            self.thread = Thread(target=self.work)
            self.thread.daemon = True
            self.thread.start()
        self.logger.info("FrameWorker started.")
        
        
    def work(self, frameQ, ns, kfl, ufl):
        from facerecognizer import FaceRecognizer

        #called in separate Thread to work on pipeline
        self.presenceDetector = PresenceDetector()
        self.faceReconizer = FaceRecognizer()
        while True:
            #self.logger.info("Pipeline Length: %d", pipe.qsize())

            #ret, frame = self.pipeline.getFrame()
            
            
            if not frameQ.empty():#ret:
                frame = frameQ.get()
                
                ns.lastFrame=frame
                ns.processedFrames += 1
                ns.idle=False
                #self.logger.info("Got frame, start Face recognition.")
                if self.newSession:
                    #new working session started
                    self.logger.info("Starting new working session")
                    self.startNewSession(kfl,ufl,ns)                    
                    self.newSession = False

                self.logger.info("Received Frame. Start Face Recognition. Timestamp: %s", time.ctime(frame.timestamp))
                startTime = time.time()
                self.faceReconizer.detectFaces(frame)                
                ns.workingFPS = 1/(time.time() - startTime)
                self.logger.info("Frame Processed with FPS: %f. ", ns.workingFPS)
                self.presenceDetector.detectPresence(frame,kfl,ufl,ns.presence)
                
                if ns.presence:
                    self.OHInterface.setPresent(self.getLastKnown().name)                    


                #if presence is detected and detectKnownThenStop flag is true, break current worker session
                if ns.presence and self.detectKnownThenStop:
                    self.logger.info("Presence set. Stop streaming. Flush videoQ")
                    #self.pipeline.stopAndFlush()     
                    #TODO need to setup pipe between video proceee and sthi    
                
            else:
                self.logger.info("No Frame on Queue. Sleeping")
                ns.idle=True
                #if not self.newSession and not self.pipeline.isStreaming:
                    #self.logger.info("Ending working session. Cleaning Up.")
                    #just got out of working session
                    #self.newSession = True
                    #send unknown notification
                    #self.presenceDetector.alertUnknown()
                    #DO NOT delete unonwns and knons list here, otherwise gone for server
                time.sleep(1) #important to sleep. otherwise locking battle on queue
                
                
           
            

