#Class to stream and store video files from webcams (or files) to memory (Queue)
#Streamer function works in separate thread/function and operates on threadsafe Queue

import cv2
import time
import sys
import configparser
config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['VIDEOPIPELINE']
if cf.getboolean('MULTIPROC'):
    import multiprocessing
    from multiprocessing import Process, Queue

else:
    from threading import Thread
    if sys.version_info >= (3, 0):
        from queue import Queue
    else:
        from Queue import Queue

from frame import Frame
import logging
from logging.config import fileConfig





class VideoPipeline:
    def __init__(self, streamTime=10):
        #max length of videpipeline. assuming 640x480 RGB frames = 500MB at 500,
        #capturing at 11fps, 10s -> 5 captures possible
        self.bufferSize=cf.getint('BUFFERSIZE')  
        self.streamTime=streamTime

        self.videoCapture = None
        self.thread = None 
        self.process = None 
        self.startTime = None
        self.Q = Queue()
        self.isStreaming = False #semaphore for single streaming only
        self.streamingFPS = 0
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("VideoPipeline")
        self.lastRun = 0


    def startStreaming(self, stringURL, streamTime = 10):
        #check and set semaphore
        if self.isStreaming: 
            self.logger.error("Only one stream at a time allowed")
            return 
        else:
            self.isStreaming = True
            self.lastRun = time.time()
        #set stream time. TODO this is not threadsafe.
        self.streamTime = streamTime

        if stringURL == "0":
            self.logger.info("Capturing from internal cam. For %d s", self.streamTime)
            self.videoCapture = cv2.VideoCapture(0) #get stream from webcam in laptop
        else:
            self.logger.info("Capturing from %s. For %d s",stringURL, self.streamTime)
            self.videoCapture = cv2.VideoCapture(stringURL)        
        self.startTime = time.time()

        if cf.getboolean('MULTIPROC'):
            #for multiprocessing
            #multiprocessing.set_start_method('spawn') #not working
            self.logger.info("Setting up Sub-Process for streaming")
            self.process = Process(target=self.streamToBuffer)
            self.process.daemon = True
            self.process.start()
        else:
            self.logger.info("Setting up Thread for streaming")
            # start a thread to capture the stream
            self.thread = Thread(target=self.streamToBuffer)
            self.thread.daemon = True
            self.thread.start()
        
        
    def streamToBuffer(self):
        #does the frame capturing.
        self.logger.info("Self Test: %d, %d",self.startTime, self.isStreaming)
        sessionFrameCounter = 0
        while (time.time()-self.startTime < self.streamTime and self.isStreaming):
            
            ret, frame = self.videoCapture.read()
            
            if ret:
                #check again if isStreaming, since during waiting for frame from Cam, flush could have happend.
                #need to avoid that after flush, new frame is put on queue. otherwise new working session will start
                self.logger.info("Checking buffer: %d.",self.bufferSize)
                if self.isStreaming and self.Q.qsize()<self.bufferSize:
                    self.Q.put(Frame(frame))
                    self.logger.info("Put on Queue: Length: %d",self.Q.qsize())
                    #print("Put on Queue. Length {}.".format(self.Q.qsize()))
                    sessionFrameCounter += 1
            else:
                self.logger.error("No Capture possible. Breaking")
                break #this should work for both file reading and streaming from cam
        self.streamingFPS = sessionFrameCounter/(time.time()-self.startTime)
        self.logger.info("Captured %d frames in %fs. StreamingFPS: %f.", sessionFrameCounter, (time.time()-self.startTime), self.streamingFPS)
        self.videoCapture.release()
        self.isStreaming = False
    
    def getLength(self):
        return self.Q.qsize()

    def getFrame(self):
        #returns the top frame from buffer
        QState = False
        frame = None
        if not self.Q.empty():
            frame = self.Q.get()
            QState = True         
        
        #print("Get From Queue. Length {}. Possible: {}.".format(self.Q.qsize(),QState))
        return QState, frame
        
    def stopAndFlush(self):
        self.isStreaming = False
        with self.Q.mutex:
            self.Q.queue.clear()

    def getLastRun(self):
        return time.ctime(self.lastRun)