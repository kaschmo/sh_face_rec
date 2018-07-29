#class to handle presence detection based on processed frames
import dlib
from math import sqrt
import logging
from logging.config import fileConfig
import multiprocessing
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
        
        self.ignoreFaceList = ["painting"]
        self.max_unknownList = cf.getint('MAX_UNKNOWNS') #restrict number on unknown faces to store to 10
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("PresenceDetector")

    def detectPresence(self, frame, kfl,ufl,ns):
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

                    #check if already in known faces
                    newFace = True
                    for fl in range(len(kfl)):
                        if kfl[fl].name == face.name:
                            self.logger.info(" %s already detected.", face.name)
                            newFace = False
                    if newFace:
                        self.logger.info("New Person %s. Adding to list", face.name)
                        kfl.append(face)
                        ns.newPresence = True

                    ns.sessionPresence=True                
                else:
                    self.logger.info("Unknowns in frame")
                    #check if face is already in unknown list
                    unknown_treshold = cf.getfloat('UNKNOWN_SAME')
                    inList = False
                    for fl in range(len(ufl)):
                        distance = self.euclidean_dist(ufl[fl].encoding, face.encoding)
                       
                        if distance < unknown_treshold:
                            inList = True
                            self.logger.info("Unknown already in list")
                            break
                    if not inList and len(ufl) < self.max_unknownList:
                        ufl.append(face)
                        self.logger.info("Unknown not yet in list. Adding. Length: %d", len(ufl))
                        
        else:
            self.logger.info("Frame contains no faces")
    
    

    

    

    #helper function to calculate eucleadian distance, since numpy.norm does not work on dlib vectors
    def euclidean_dist(self, vector_x, vector_y):
        if len(vector_x) != len(vector_y):
            raise Exception('PresenceDetector: Vectors must be same dimensions')
        return sum((vector_x[dim] - vector_y[dim]) ** 2 for dim in range(len(vector_x)))

    
