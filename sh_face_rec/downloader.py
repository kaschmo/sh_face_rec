#Class to download videos from stream and write to filesystem.
#TODO Improve: use videopipeline component and then simply save file.

import time
import cv2
import sys
if sys.version_info >= (3, 0):
    from queue import Queue
else:
    from Queue import Queue
from threading import Thread
import logging
from logging.config import fileConfig
import numpy as np
import configparser

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['DOWNLOADER']

class Downloader:
    def __init__(self):
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("Downloader")
        self.videoCapture = None
        self.isStreaming = False #semaphore for single streaming only
        self.streamingFPS = 0
        self.thread = None
        self.Q = Queue()
        self.downloadPath = cf['DOWNLOAD_PATH']


    def download(self, URL, streamTime, filename):
        
        if self.isStreaming: 
            self.logger.error("Only one stream at a time allowed")
            return 
        else:
            self.isStreaming = True
        self.startTime = time.time()
        self.streamTime = streamTime
        self.filename = self.downloadPath + filename
        self.videoCapture = cv2.VideoCapture(URL)
        
        self.thread = Thread(target=self.streamToBuffer)
        self.thread.daemon = True
        self.thread.start()

    def streamToBuffer(self):
        sessionFrameCounter = 0
        while (time.time()-self.startTime < self.streamTime):            
            ret, frame = self.videoCapture.read()
            
            if ret:     
                self.Q.put(frame)
                sessionFrameCounter += 1
            else:
                self.logger.error("No Capture possible. Breaking")
                break #this should work for both file reading and streaming from cam
        self.streamingFPS = int(sessionFrameCounter/(time.time()-self.startTime))
        self.logger.info("Captured %d frames in %fs. StreamingFPS: %f.", sessionFrameCounter, (time.time()-self.startTime), self.streamingFPS)
        self.videoCapture.release()
        self.isStreaming = False
        res = np.transpose(frame).shape[1:3] #reversing resolution. assuming format (480, 640, 3)
        fourcc_format=cf['FOURCC']
        fourcc = cv2.VideoWriter_fourcc(*'MJPG') #TODO
        #fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        self.logger.info("Storing to %s at FPS %d and Resolution %s", self.filename, self.streamingFPS, str(res))
        #cv2.VideoWriter('output.avi', fourcc, 11, (640, 480))
        output_movie = cv2.VideoWriter(self.filename, fourcc, self.streamingFPS, res) #frame.shape[0:2])
        while (self.Q.qsize()!=0):
            output_movie.write(self.Q.get())
