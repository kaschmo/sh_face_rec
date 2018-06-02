import cv2
import dlib
import sys
from frame import Frame
import numpy as np

class FrameViewer:
    def __init__(self):
        self.knownBBcolor = (0, 255, 0) #green
        self.unknownBBcolor = (0, 0, 255) #red
        self.BBthickness = 1
        self.BBlineType = 8

    def getShapeCoords(self, dlib_shape, dtype="int"):
        #assuming 5point landmark
        
        coords = np.zeros((5, 2), dtype=dtype)
    
        for i in range(0, 5):
            coords[i] = (dlib_shape.part(i).x, dlib_shape.part(i).y)
        return coords

    def viewFaceChipsInFrame(self, frame):
        #show image face snapshots
        BGRframe = frame.getBGR()

        for i in range(len(frame.faceLocations)):
            #add shape landmark points to frame for current face
            shape = self.getShapeCoords(frame.faceLandmarks[i])
            for (x, y) in shape:
		        cv2.circle(BGRframe, (x, y), 1, (0, 0, 255), -1)
            RGBframe = cv2.cvtColor(BGRframe, cv2.COLOR_BGR2RGB)
            curface = dlib.get_face_chip(RGBframe, frame.faceLandmarks[i], size=150)
            bgrFace = cv2.cvtColor(curface, cv2.COLOR_RGB2BGR) #convert back to bgr for cv
            faceLocation = frame.faceLocations[i]
            #print(faceLocation)
            x= faceLocation.right() - faceLocation.left()
            y= faceLocation.bottom() - faceLocation.top()
            curName = frame.faceNames[i] + "("+str(frame.faceDistances[i])+") (" + str(x)+"x"+str(y)+")"
            cv2.imshow(curName,bgrFace)

    def viewFrame(self, frame):
        BGRframe = frame.getBGR()  
        for i in range(len(frame.faceLocations)):
                  
            # Draw a box around the face
            if frame.faceNames[i] == "unknown":
                #draw red
                cv2.rectangle(BGRframe, (frame.faceLocations[i].left(), frame.faceLocations[i].top()), (frame.faceLocations[i].right(), frame.faceLocations[i].bottom()), self.unknownBBcolor, thickness = self.BBthickness, lineType=self.BBlineType)
            else:
                #draw green
                cv2.rectangle(BGRframe, (frame.faceLocations[i].left(), frame.faceLocations[i].top()), (frame.faceLocations[i].right(), frame.faceLocations[i].bottom()), self.knownBBcolor, thickness = self.BBthickness, lineType=self.BBlineType)

            # Draw a label with a name below the face
            font = cv2.FONT_HERSHEY_PLAIN
            printText=frame.faceNames[i] + " ({:.2f})".format(frame.faceDistances[i])
            
            #print in white
            cv2.putText(BGRframe, printText, (frame.faceLocations[i].left() + 6, frame.faceLocations[i].bottom() + 20), font, 1.0, (255, 255, 255), 1)
        cv2.namedWindow("FrameX", cv2.WINDOW_NORMAL)
        cv2.imshow("FrameX",BGRframe)
        return BGRframe
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()