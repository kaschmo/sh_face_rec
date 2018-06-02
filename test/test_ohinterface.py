#Testcases for OpenHAB interface class
import unittest

from sh_face_rec.ohinterface import OHInterface

class InterfaceTest(unittest.TestCase):
    def setUp(self):
        #do some init
        testIP = '192.168.1.10'
        testport = '8080'
        self.OHIF = OHInterface(testIP, testport)

    def test_PresenceCall(self):
        print("Testing OHInterface")        
        ret = self.OHIF.setPresent("karsten")
        self.assertEqual(ret,'200') 

    def test_UnknownCall(self):
        ret = self.OHIF.unknownAlert(10)
        self.assertEqual(ret, '200') 


