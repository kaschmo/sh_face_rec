#class to handle presence detection based on processed frames
import dlib
from math import sqrt
import logging
from logging.config import fileConfig
#from multiprocessing import Process, Queue

from frame import Frame
from ohinterface import OHInterface
from face import Face

import configparser

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['PRESENCEDETECTOR']

class PresenceDetector:
    def __init__(self):
        self.lastKnownFace = None #to store Name with last face. TODO: this is not thread safe? Also how to store multiole faces?
        self.knownFaceList = []
        self.unknownFaceList = []
        self.OHInterface = OHInterface()
        self.presence = False
        self.ignoreFaceList = ["painting"]
        self.max_unknownList = cf.getint('MAX_UNKNOWNS') #restrict number on unknown faces to store to 10
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("PresenceDetector")

    def detectPresence(self, frame):
        if frame.hasFace:
            #FUTURE: harder acceptance criteria for presence?
            #FUTURE: this approach only detects one person!
            #TODO: work with face_ignore_liste for Painting

            for i in range(len(frame.faceNames)):
                faceChip = dlib.get_face_chip(frame.getRGB(), frame.faceLandmarks[i])
                face = Face(img = faceChip, name = frame.faceNames[i], timestamp = frame.timestamp, encoding = frame.faceEmbeddings[i], distance = frame.faceDistances[i])
                if face.name != 'unknown': 
                    if face.name == self.ignoreFaceList[0]: 
                        self.logger.info("Ignoring %s.", face.name)   
                        continue                                       
                    self.lastKnownFace = face 
                    newFace = True
                    for fl in range(len(self.knownFaceList)):
                        if self.knownFaceList[fl].name == face.name:
                            self.logger.info(" %s already detected.", face.name)
                            newFace = False
                    if newFace:
                        self.logger.info("New Person %s. Adding to list", face.name)
                        self.knownFaceList.append(face)
                        #trigger OH
                        self.OHInterface.setPresent(face.name)                    
                                        
                    self.presence = True
                else:
                    self.logger.info("Unknowns in frame")
                    #check if face is already in unknown list
                    unknown_treshold = cf.getfloat('UNKNOWN_SAME')
                    inList = False
                    for ufl in range(len(self.unknownFaceList)):
                        distance = self.euclidean_dist(self.unknownFaceList[ufl].encoding, face.encoding)
                       
                        if distance < unknown_treshold:
                            inList = True
                            self.logger.info("Unknown already in list")
                            break
                    if not inList and len(self.unknownFaceList) < self.max_unknownList:
                        self.unknownFaceList.append(face)
                        self.logger.info("Unknown not yet in list. Adding. Length: %d", len(self.unknownFaceList))
                        
        else:
            self.logger.info("Frame contains no faces")
    
    def alertUnknown(self):
        if self.getUnknownCount()> 0 and not self.presence:
            self.OHInterface.unknownAlert(self.getUnknownCount())

    def newSession(self):
        #reset/delete all lists of known and unknoen faces.
        self.logger.info("Resetting Session")
        self.lastKnownFace = None
        self.knownFaceList = []
        self.unknownFaceList = []
        self.presence = False

    def getKnownFromList(self, index):
        if index < len(self.knownFaceList):
            return self.knownFaceList[index]
        else:
            #TODO Execption
            return None

    def getLastKnown(self):
        return self.getKnownFromList(len(self.knownFaceList)-1)

    def getUnknownFromList(self, index):
        if index < len(self.unknownFaceList):
            return self.unknownFaceList[index]
        else:
            #TODO Execption
            return None

    def getLastUnknown(self):
        return self.getUnknownFromList(len(self.unknownFaceList)-1)

    #helper function to calculate eucleadian distance, since numpy.norm does not work on dlib vectors
    def euclidean_dist(self, vector_x, vector_y):
        if len(vector_x) != len(vector_y):
            raise Exception('PresenceDetector: Vectors must be same dimensions')
        return sum((vector_x[dim] - vector_y[dim]) ** 2 for dim in range(len(vector_x)))

    def getKnownCount(self):
        return len(self.knownFaceList)

    def getUnknownCount(self):
        return len(self.unknownFaceList)
