#Helper Class with all face recognition functions and models that are required.
#Performs
#- Face Detection
#- Face Landmark Prediction
#- Face Encoding
#- Face Classification

import numpy as np
from sklearn import neighbors
import pickle
import time
import logging
from logging.config import fileConfig

import dlib
import cv2
import scipy.misc
import sys

from frame import Frame
from mtcnndetector import MTCNNDetector

import configparser

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['FACERECOGNIZER']

class FaceRecognizer:
    #Class variables that hold for all instances of FaceRecognizer
    model_path=cf['MODEL_PATH']
    #Face Detection CNN Model and variables
    #dlib_cnn_face_detection_model = model_path + "mmod_human_face_detector.dat" #in same folder as .py. also available in dlib install folder?
    #cnn_face_detector = dlib.cnn_face_detection_model_v1(dlib_cnn_face_detection_model)
    #cnn_face_detector_upsample=1

    #Face Detection Hog Detector. No Model
    #HOG_face_detector = dlib.get_frontal_face_detector()

    #MTCNN detector
    MTCNN_face_detector = MTCNNDetector(minsize = cf.getint('MTCNN_MINSIZE'), thresholds = [0.6, 0.7, 0.8], scale_factor = cf.getfloat('MTCNN_SCALE_FACTOR'), bb_margin = cf.getint('MTCNN_BB_MARGIN'))

    #Models for landmark description
    predictor_68_point_model = model_path + "shape_predictor_68_face_landmarks.dat"
    #pose_predictor_68_point = dlib.shape_predictor(predictor_68_point_model)
    predictor_5_point_model = model_path + "shape_predictor_5_face_landmarks.dat"
    #pose_predictor_5_point = dlib.shape_predictor(predictor_5_point_model)
    if cf['LANDMARK_DET'] == "68_point":
        pose_predictor = dlib.shape_predictor(predictor_68_point_model)
    else:
        pose_predictor = dlib.shape_predictor(predictor_5_point_model)
    #Model 128byte embedding generation
    face_recognition_model = model_path + "dlib_face_recognition_resnet_model_v1.dat"
    face_encoder = dlib.face_recognition_model_v1(face_recognition_model)
    face_encoding_num_jitters=1 #how many times to resample when ecoding.

    #Classifier Model for KNN classifier
    knn_model_path=model_path + cf['KNN_MODEL_NAME']
    #allowed distance for recognition
    knn_distance_threshold=cf.getfloat('KNN_TRESHOLD')


    def __init__(self):
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("FaceRecognizer")
        self.logger.info("Initializing MTCNN Detector")
        #init required models        
        with open(self.knn_model_path, 'rb') as f:
            self.knn_clf = pickle.load(f)
        
    
    def detectFaces(self, frame):
        frame.hasFace = False
        #HOG based - works directly as dlib.rect        
        #frame.faceLocations = self.HOG_face_detector(frame.getRGB(), self.cnn_face_detector_upsample)

        #MTCNN based
        frame.faceLocations = self.MTCNN_face_detector.detect(frame)
        #self.logger.info("Passed MTCNN")
        #iterate over all detected faces and do encoding
        for face_location in frame.faceLocations:
            #get landmarks and add to frame
            raw_landmark = self.pose_predictor(frame.getRGB(), face_location) 
            frame.faceLandmarks.append(raw_landmark)
            #encode face and add to frame
            face_embedding = self.face_encoder.compute_face_descriptor(frame.getRGB(), raw_landmark, self.face_encoding_num_jitters)
            frame.faceEmbeddings.append(face_embedding)
        #self.logger.info("Passed Encoding")
        #classify if faces encodings exists
        if len(frame.faceEmbeddings) > 0:  
            frame.hasFace = True
            closest_distances = self.knn_clf.kneighbors(frame.faceEmbeddings, n_neighbors=1)
            frame.faceNames=self.knn_clf.predict(frame.faceEmbeddings)
            #iterate over all facess and check if distance smaller treshhold. returns Bool vector length X (faces)
            for i in range(len(frame.faceEmbeddings)):
                distance = (closest_distances[0][i][0])
                frame.faceDistances.append(distance)
                if distance > self.knn_distance_threshold:
                    frame.faceNames[i]="unknown"
                else:
                    x= frame.faceLocations[i].right() - frame.faceLocations[i].left()
                    y= frame.faceLocations[i].bottom() - frame.faceLocations[i].top()
                    faceLocString = "(" + str(x)+"x"+str(y)+")"
                    self.logger.info("Detected %s (%f) Size %s at %s", frame.faceNames[i], frame.faceDistances[i],faceLocString,time.ctime(frame.timestamp))                    
    