# -*- coding: utf-8 -*-
#RUN python sh_face_rec/trainclassifier.py 
#script to train a new knn classifier using sklearn knn neighbor algorithm.
#requires folder structure with images in train_dir. outputs to model_path
#train_dir
#-label1 folder
#--img1
#--img2
#-label2 folder
#--img1

import math
from sklearn import neighbors
import os
import os.path
import re
import pickle
import time
import logging
from logging.config import fileConfig
import cv2
import dlib
from mtcnndetector import MTCNNDetector
from frame import Frame
import configparser


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')

cf = config['TRAIN']
train_dir = cf["TRAINING_PATH"]

cf = config['FACERECOGNIZER']
model_dir = cf['MODEL_PATH']
model_name = "180628_knn_model_py3"
n_neighbors=3
knn_algo='ball_tree'
fileConfig('sh_face_rec/logging.conf')
logger = logging.getLogger("trainClassifier")
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)


MTCNN_face_detector = MTCNNDetector(minsize = cf.getint('MTCNN_MINSIZE'), thresholds = [0.6, 0.7, 0.8], scale_factor = cf.getfloat('MTCNN_SCALE_FACTOR'), bb_margin = cf.getint('MTCNN_BB_MARGIN'))

#MTCNN_face_detector = MTCNNDetector(minsize = 40, thresholds = [0.6, 0.7, 0.8], scale_factor = 0.709, bb_margin = 20)
predictor_68_point_model = model_dir + "shape_predictor_68_face_landmarks.dat"
#pose_predictor_68_point = dlib.shape_predictor(predictor_68_point_model)
predictor_5_point_model = model_dir + "shape_predictor_5_face_landmarks.dat"
#pose_predictor_5_point = dlib.shape_predictor(predictor_5_point_model)
if cf['LANDMARK_DET'] == "68_point":
    pose_predictor = dlib.shape_predictor(predictor_68_point_model)
else:
    pose_predictor = dlib.shape_predictor(predictor_5_point_model)

face_recognition_model = model_dir + "dlib_face_recognition_resnet_model_v1.dat"
face_encoder = dlib.face_recognition_model_v1(face_recognition_model)
face_encoding_num_jitters=1 #how many times to resample when ecoding.

def image_files_in_folder(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if re.match(r'.*\.(jpg|jpeg|png)', f, flags=re.I)]


if __name__ == "__main__":
    logger.info("Training knn model in %s", os.path.join(model_dir, model_name))
    X = []
    y = []
    start=time.time()
    num_img=0
    # Loop through each person in the training set
    for class_dir in os.listdir(train_dir):
        if not os.path.isdir(os.path.join(train_dir, class_dir)):
            continue

        # Loop through each training image for the current person
        for img_path in image_files_in_folder(os.path.join(train_dir, class_dir)):
            image = cv2.imread(img_path)
            frame = Frame(image)
            face_locations = MTCNN_face_detector.detect(frame)

            if len(face_locations) != 1:
                # If there are no people (or too many people) in a training image, skip the image.
                logger.warning("Image %s not suitable for training. Faces: %d", img_path, len(face_locations))
            else:
                # Add face encoding for current image to the training set
                raw_landmark = pose_predictor(frame.getRGB(), face_locations[0]) 
                logger.info("Labelling image %s with %s", img_path, class_dir)
                #encode face and add to frame
                face_embedding = face_encoder.compute_face_descriptor(frame.getRGB(), raw_landmark, face_encoding_num_jitters)
                X.append(face_embedding)
                y.append(class_dir)
                num_img+=1

    # Determine how many neighbors to use for weighting in the KNN classifier
    if n_neighbors is None:
        n_neighbors = int(round(math.sqrt(len(X))))
        logger.info("Chose n_neighbors automatically: %d", n_neighbors)

    # Create and train the KNN classifier
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
    knn_clf.fit(X, y)

    # Save the trained KNN classifier
    with open(os.path.join(model_dir, model_name), 'wb') as f:
        pickle.dump(knn_clf, f)

    logger.info("Training done. used %d pictures. Took %f s",num_img, time.time()-start)

    