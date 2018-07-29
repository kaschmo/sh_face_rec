#Testcases for frameworker #python -m unittest test.test_frameworker

import unittest

import cv2
import sh_face_rec
from sh_face_rec.frame import Frame
from sh_face_rec.videopipeline import VideoPipeline
from sh_face_rec.frameworker import FrameWorker
import dlib 


class FrameworkerTest(unittest.TestCase):
    def test_frameworker(self):
        print("Testing frameworker")
        pipeline = VideoPipeline()
        frameWorker = FrameWorker()
        testimgfile = "./test/testimages/wellies.jpg"
        pipeline.startStreaming(testimgfile)
        print("Queue: {}".format(pipeline.getLength()))
        frameWorker.start(pipeline)
