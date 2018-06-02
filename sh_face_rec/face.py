#class to model faces (image, timestamp, name)
import time

class Face:
    def __init__(self, img, name, timestamp, encoding, distance):
        self.timestamp = timestamp
        self.__RGBimg__ = img
        self.name = name
        self.encoding = encoding
        self.distance = distance

    def getRGB(self):
        #for dlib
        return self.__RGBimg__

    def getBGR(self):
        #for opencv
        return self.__RGBimg__[:, :, ::-1]

    def getCTime(self):
        #readable time format
        return time.ctime(self.timestamp)