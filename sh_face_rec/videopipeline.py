#Class to stream and store video files from webcams (or files) to memory (Queue)
#Streamer function works in separate thread/function and operates on threadsafe Queue

import cv2
import time
import sys
import configparser
config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['VIDEOPIPELINE']

import multiprocessing
from multiprocessing import Process, Queue


from frame import Frame
import logging
from logging.config import fileConfig





class VideoPipeline:
    def __init__(self, streamTime=10):
        #max length of videpipeline. assuming 640x480 RGB frames = 500MB at 500,
        #capturing at 11fps, 10s -> 5 captures possible
        self.bufferSize=cf.getint('BUFFERSIZE')  
        self.streamTime=streamTime

        self.process = None 
        self.startTime = None
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("VideoPipeline")
        self.logger.info("Started Videopipeline")

        self.lastRun = 0

        #multiproc
        self.Q = Queue(cf.getint('BUFFERSIZE'))
        self.manager = multiprocessing.Manager()
        self.globalns = self.manager.Namespace()
        #self.globalns.videoCapture = None
        self.globalns.stringURL = ""
        self.globalns.streamingFPS = 0
        self.globalns.isStreaming = False
        self.globalns.cap_frames = 0

    def getStreamingFPS(self):
        return self.globalns.streamingFPS

    def getStreaming(self):
        return self.globalns.isStreaming

    def startStreaming(self, stringURL, streamTime = 10):
        #check and set semaphore
        if self.globalns.isStreaming: 
            self.logger.error("Only one stream at a time allowed")
            return 
        
        self.globalns.isStreaming = True
        self.lastRun = time.time()
        #OK to have global vars, since only one concurrent streaming process always active.
        self.streamTime = streamTime

        self.globalns.stringURL = stringURL  
        self.globalns.cap_frames = 0    
        self.startTime = time.time()

            
        self.logger.info("Setting up Sub-Process for streaming")
        self.process = Process(target=self.streamToBuffer, args=(self.Q, self.globalns))
        self.process.daemon = True
        self.process.start()
        self.process.join()        
        
        
    def streamToBuffer(self, frameQ, ns):
        #does the frame capturing.
        self.logger.info("Self Test: startTime: %d, isStreaming: %d, streamTime: %d",self.startTime, self.globalns.isStreaming, self.streamTime)
        sessionFrameCounter = 0
        if ns.stringURL == "0":
            self.logger.info("Capturing from internal cam. For %d s", self.streamTime)
            videoCapture = cv2.VideoCapture(0) #get stream from webcam in laptop
        else:
            self.logger.info("Capturing from %s. For %d s",ns.stringURL, self.streamTime)
            videoCapture = cv2.VideoCapture(ns.stringURL)  
            #this init calls takes long time on Rpi: 7-12s
        self.logger.info("CV2 Opened: %d, CV2 Buffer size: %d",	videoCapture.isOpened(), videoCapture.get(cv2.CAP_PROP_BUFFERSIZE))

        #workaround that streaming will happen even though when initialization of VideoCapture takes too long
        min_fps = cf.getint('MIN_FPS')
        min_frames = self.streamTime * min_fps
        while ((time.time()-self.startTime < self.streamTime and ns.isStreaming) or sessionFrameCounter < min_frames):
            
            ret, frame = videoCapture.read()
            if ret:
                #check again if isStreaming, since during waiting for frame from Cam, flush could have happend.
                #need to avoid that after flush, new frame is put on queue. otherwise new working session will start
                #self.logger.info("Checking buffer: %d.",self.bufferSize)
                if ns.isStreaming and not frameQ.full(): 
                    frameQ.put(Frame(frame))
                    #self.logger.info("Put on Queue: Length: %d",self.Q.qsize())
                    #print("Put on Queue. Length {}.".format(self.Q.qsize()))
                    sessionFrameCounter += 1
            else:
                self.logger.error("No Capture possible. Breaking")
                break #this should work for both file reading and streaming from cam
       
        self.globalns.streamingFPS = sessionFrameCounter/(time.time()-self.startTime)
        self.logger.info("Captured %d frames in %fs. StreamingFPS: %f.", sessionFrameCounter, (time.time()-self.startTime), self.globalns.streamingFPS)
        videoCapture.release()
        ns.isStreaming = False
    
    def getLength(self):
        self.logger.error("Not implemented")
        #return self.Q.qsize()

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
        self.globalns.isStreaming = False
        with self.Q.mutex:
            self.Q.queue.clear()

    def getLastRun(self):
        return time.ctime(self.lastRun)