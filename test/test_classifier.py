#Standalone test to run the whole face detection, recognition,  classification pipeline
#Does not assert anything
#visualizes the resulting frames for visual inspection
#uses same configuration/models as production code
#RUN python -m unittest test.test_classifier
#can be used to write resulting video to file
import unittest
import cv2
from sh_face_rec.facerecognizer import FaceRecognizer
from sh_face_rec.frame import Frame
from sh_face_rec.frameviewer import FrameViewer
import configparser

class ClassifierTest(unittest.TestCase):
    def test_classifier(self):
        config = configparser.ConfigParser()
        config.read('sh_face_rec/config.ini')
        cf = config['TEST']

        writeToFile = True    
        FR = FaceRecognizer()
        FV = FrameViewer()
        #video_path="/Users/karsten/Downloads/train_videos/"
        video_path=cf["TEST_VIDEO_PATH"]
        #video_path="/Users/karsten/Documents/00_Project_Support/180323_FaceRecognition/04_face_recognition_lib/videos/"
        testvideo = "blog_k2.avi"
        #testvideo = "test_karsten_close.avi"
        #testvideo = "test_mara_bw_fast.avi"
        #testvideo = "180412_hall_rgb4.avi"
        

        videoCapture = cv2.VideoCapture(video_path + testvideo)

        #for writing output
        writefile = "output_classifier.avi"
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        fps = videoCapture.get(cv2.CAP_PROP_FPS)
        res = (640,480)
        #res = np.transpose(frame).shape[1:3]
        output_movie = cv2.VideoWriter(video_path + writefile, fourcc, fps, res)

        while True:
            ret, frame = videoCapture.read()

            if ret:
                testFrame = Frame(frame)
                FR.detectFaces(testFrame)         
                BGRframe = FV.viewFrame(testFrame)
                #write to file
                if writeToFile:
                    output_movie.write(BGRframe)      

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("Error: could not open or file end")
                break

        videoCapture.release()
        cv2.destroyAllWindows()

