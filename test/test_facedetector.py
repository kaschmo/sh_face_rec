#Testcases for mtcnn facetector
#python -m unittest test.test_facedetector
import unittest
import cv2
from sh_face_rec.mtcnndetector import MTCNNDetector
from sh_face_rec.frame import Frame
import dlib 
import configparser


class DetectorTest(unittest.TestCase):
    def test_facedetector(self):
        print("Testing MTCNNDetector.detect")
        config = configparser.ConfigParser()
        config.read('sh_face_rec/config.ini')
        cf = config['TEST']
        img_path=cf["TEST_IMG_PATH"]

        MTCNN_face_detector = MTCNNDetector(minsize = 20, thresholds = [0.6, 0.7, 0.8], scale_factor = 0.709, bb_margin = 20)

        testimg= "wellies.jpg"
        location_array = [dlib.rectangle(2321,872,2716,1281), dlib.rectangle(1270,569,1686,1135), dlib.rectangle(1999,1399,2276,1735), dlib.rectangle(764,690,855,825)]
        videoCapture = cv2.VideoCapture(img_path + testimg)
        ret, frame = videoCapture.read()
        if ret:
            testFrame = Frame(frame)
            testFrame.faceLocations = MTCNN_face_detector.detect(frame)
            self.assertItemsEqual(testFrame.faceLocations, location_array)
            
        else:
            print("Error: could not open")



