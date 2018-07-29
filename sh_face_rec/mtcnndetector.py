#Wrapper Module to work with davidsandbergs facenet align mtcnn face detector.

import numpy as np
from sklearn import neighbors
import pickle
import time

import dlib
import cv2
import scipy.misc
import logging
from logging.config import fileConfig

import tensorflow as tf
import align.detect_face #TODO

from frame import Frame


class MTCNNDetector:
    def __init__(self, minsize = 20, thresholds = [0.6, 0.7, 0.8], scale_factor = 0.709, bb_margin = 20):
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("MTCNNDetector")
        self.logger.info('Creating networks and loading parameters')    
        with tf.Graph().as_default():
            #Upper bound on the amount of GPU memory that will be used by the process.'
            gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=1.0)
            sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
            with sess.as_default():
                self.pnet, self.rnet, self.onet = align.detect_face.create_mtcnn(sess, None)

        self.minsize = minsize # minimum size of face
        self.threshold = thresholds  # three steps's threshold
        self.factor = scale_factor # scale factor
        self.bb_margin=bb_margin #margin to add to bounding boxes
        

    def detect(self, frame):
        #self.logger.info("Detecting Faces")
        rgbframe = frame.getRGB()
        frame_size = np.asarray(rgbframe.shape)[0:2]

        bounding_boxes, _ = align.detect_face.detect_face(rgbframe, self.minsize, self.pnet, self.rnet, self.onet, self.threshold, self.factor)

        #convert to dlib rectangles
        face_locations = []
        det = bounding_boxes[:,0:4] #only take coordinates
        nrof_faces = bounding_boxes.shape[0]
        for i in range(nrof_faces):
            loc = np.squeeze(det[i]).astype(int) #convert float to ints
            #add margin to boundingbox            
            loc[0] = loc[0]-np.maximum(self.bb_margin/2,0) 
            loc[1] = loc[1]-np.maximum(self.bb_margin/2,0) 
            loc[2] = loc[2]+np.minimum(self.bb_margin/2,frame_size[1]) 
            loc[3] = loc[3]+np.minimum(self.bb_margin/2,frame_size[0]) 
            face_locations.append(dlib.rectangle(loc[0],loc[1],loc[2],loc[3]))

        return face_locations