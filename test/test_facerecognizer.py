#Testcases for facerecognizer class
#Displays the image and all recognized faces in separate windows
import unittest
import cv2
from sh_face_rec.facerecognizer import FaceRecognizer
from sh_face_rec.frame import Frame
from sh_face_rec.frameviewer import FrameViewer
import configparser

class DetectorTest(unittest.TestCase):
    def test_facerecognition(self):
        print("Testing FaceRecognizer.detectFace")
        config = configparser.ConfigParser()
        config.read('sh_face_rec/config.ini')
        cf = config['TEST']
        img_path=cf["TEST_IMG_PATH"]
        testimg = "blog1.png"
        FR = FaceRecognizer()
        FV = FrameViewer()
        
        testimgnames = ['karsten', 'miriam', 'unknown', 'unknown']
        frame = cv2.imread(img_path + testimg)
        ret=True
        if ret:
            testFrame = Frame(frame)
            FR.detectFaces(testFrame)
            
            for i in range(len(testFrame.faceNames)):
                print(testFrame.faceNames[i])
            
            FV.viewFaceChipsInFrame(testFrame)
            FV.viewFrame(testFrame)
            cv2.waitKey(0)
            self.assertItemsEqual(testFrame.faceNames, testimgnames)
        else:
            print("Error: could not open")

        cv2.destroyAllWindows()

