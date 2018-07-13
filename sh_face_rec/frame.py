#Model class to represent face recognition frames from video streams
#contains image, timestamp
#will be filled up with locations, encodings, names, facechips

import cv2
import time

class Frame:
    def __init__(self, BGRimage):
        self.timestamp = time.time()
        #since working with CV2, expecting BGR image
        self.__BGRimage__ = BGRimage
        self.faceLocations = [] #dlib rects
        self.faceLandmarks = [] #needed to hand over to face objects. can be dlib 5point or 68point
        self.faceEmbeddings = [] #128D vector
        self.faceDistances = [] #scalar distance
        self.faceNames = [] #string list of names in frame
        self.hasFace = False #indicates if >0 faces in frame
        self.presence = False

    def getBGR(self):
        #for opencv
        return self.__BGRimage__
    
    def getRGB(self):
        #for dlib 
        return self.__BGRimage__[:, :, ::-1]
