from flask import Flask, make_response, request, abort,jsonify, send_file
import sys
import cv2
import time
from videopipeline import VideoPipeline
from frameworker import FrameWorker
from frame import Frame
from downloader import Downloader
import configparser
import multiprocessing
import logging
from logging.config import fileConfig



config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['STARTSERVER']
#Major Objects instantiation
pipeline = VideoPipeline()
frameWorker = FrameWorker()
downloader = Downloader()
logger = logging.getLogger("root")

frameWorker.start(pipeline) 

app = Flask(__name__)

@app.route('/')
def landingPage():
    return 'TODO: Create Landingpage with static templage for buttons.'

###---------------DETECT COMMANDS----------------
#call with curl -i -H "Content-Type: application/json" -X POST -d '{"URL":"http://192.168.0.1/video.cgi"}' http://0.0.0.0:5001/detectFrom
#internal CAM
#curl -i -H "Content-Type: application/json" -X POST -d '{"URL":"0"}' http://0.0.0.0:5001/detectFrom
#test videos
#curl -i -H "Content-Type: application/json" -X POST -d '{"URL":"../04_face_recognition_lib/videos/180412_hall_rgb4.avi"}' http://0.0.0.0:5001/detectFrom
@app.route('/detectFrom', methods = ['POST'])
def detectFrom():
    if not request.json or not 'URL' in request.json:
        abort(404)
    CamURL = request.json.get('URL',"")
    if not 'Time' in request.json:
        streamTime = 10
    else:
        streamTime = int(request.json.get('Time',""))
    if pipeline.getStreaming():
        return jsonify("Error: only one stream allowed"),400

    logger.info("Streaming request %s, %d seconds",CamURL, streamTime )
    pipeline.startStreaming(CamURL,streamTime)
    return jsonify(CamURL=CamURL),200

@app.route('/downloadFrom', methods = ['POST'])
def downloadFrom():
    if not request.json or not 'URL' in request.json:
        abort(404)
    CamURL = request.json.get('URL',"")
    if not 'Time' in request.json:
        streamTime = 10
    else:
        streamTime = int(request.json.get('Time',""))
    if not 'Filename' in request.json:
        #store file with time attached
        filename = 'stream'+str(time.time())+".avi"
    else:
        filename = request.json.get('Filename',"")
    if downloader.isStreaming:
        return jsonify("Error: only one stream allowed"),400
    downloader.download(CamURL, streamTime, filename)
    return jsonify(CamURL=CamURL),200

###---------------GENERAL STATS AND INFO----------------

#curl -i http://0.0.0.0:5001/getStats
@app.route('/getStats')
def getStats():
    logger.info("Providing stats")    
    if frameWorker.getKnownCount() > 0:
        lastKnownFace = frameWorker.getLastKnown()
        lastKnownFaceName = lastKnownFace.name
        lastKnownFaceTime = lastKnownFace.getCTime()
    else:
        lastKnownFaceName = "none"
        lastKnownFaceTime = 0
    
    
    if frameWorker.getUnknownCount() > 0:
        lastUnknownFace = frameWorker.getLastUnknown()
        lastUnknownFaceTime = lastUnknownFace.getCTime()
    else:
        lastUnknownFaceTime = 0

    return jsonify(#pipelineLength = pipeline.Q.qsize(),
                    streamingFPS = pipeline.getStreamingFPS(),
                    lastRun = pipeline.getLastRun(),
                    isStreaming = pipeline.getStreaming(),
                    workerIdle = frameWorker.getIdle(),
                    processingFPS = frameWorker.getFPS(),
                    knownCount = frameWorker.getKnownCount(),
                    unknownCount = frameWorker.getUnknownCount(),
                    lastKnownName = lastKnownFaceName,
                    lastKnownTime = lastKnownFaceTime,
                    lastUnknownTime = lastUnknownFaceTime,
                    processedFrames = frameWorker.getProcessedFrames()),200

@app.route('/getKnownCount')
def getKnownCount():
    logger.info("Providing KnownCount")
    return jsonify(knownCount = frameWorker.getKnownCount()),200

@app.route('/getUnknownCount')
def getUnknownCount():
    logger.info("Providing KnownCount")
    return jsonify(unknownCount = frameWorker.getUnknownCount()),200

###---------------KNOWN ACCESS----------------

@app.route('/getKnown/<int:index>')
def getKnown(index):
    if index == -1:
        #get last Face
        index = frameWorker.getKnownCount()-1

    if frameWorker.getKnownCount() > index: 
        KnownFace = frameWorker.getKnownFromList(index)
        KnownFaceName = KnownFace.name
        KnownFaceTime = KnownFace.getCTime()
        KnownFaceDistance = KnownFace.distance
        return jsonify(Name = KnownFaceName,
                        Time = KnownFaceTime,
                        Distance = KnownFaceDistance),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)


@app.route('/getLastKnown')
def getLastKnown():
    return getKnown(-1)

#curl -i http://0.0.0.0:5001/getLastKnownFace
@app.route('/getLastKnownFace')
def getLastKnownFace():
    return getKnownFace(-1)

@app.route('/getKnownFace/<int:index>')
def getKnownFace(index):
    if index == -1:
        #get last Face
        index = frameWorker.getKnownCount()-1
    if frameWorker.getKnownCount() > index: 
        lastFace = frameWorker.getKnownFromList(index).getBGR()
        return returnImg(lastFace),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)


###---------------UNKNOWN ACCESS----------------

@app.route('/getUnknown/<int:index>')
def getUnknown(index):
    if index == -1:
        #get last UnknownFace
        index = frameWorker.getUnknownCount()-1

    if frameWorker.getUnknownCount() > index:
        UnknownFace = frameWorker.getUnknownFromList(index)
        UnknownFaceTime = UnknownFace.getCTime()
        UnknownFaceName = UnknownFace.name
        UnknownFaceDistance = UnknownFace.distance
        return jsonify(Name = UnknownFaceName,
                        Time = UnknownFaceTime,
                        Distance = UnknownFaceDistance),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)
        
    

@app.route('/getLastUnknown')
def getLastUnknown():
    return getUnknown(-1)

@app.route('/getLastUnknownFace')
def getLastUnknownFace():    
    return getUnknownFace(-1)

#Get UnknownFace via Index
@app.route('/getUnknownFace/<int:index>')
def getUnknownFace(index):
    if index == -1:
        #get last UnknownFace
        index = frameWorker.getUnknownCount()-1
    if frameWorker.getUnknownCount() > index: 
        lastFace = frameWorker.getUnknownFromList(index).getBGR()
        return returnImg(lastFace),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)

#-----------FRAME ACCESS--------------------

@app.route('/getLastFrame')
def getLastFrame():
    logger.info("Providing LastFrame")
    if frameWorker.getLastFrame() != None: 
        return returnImg(frameWorker.getLastFrame().getBGR()),200
    else:
        return make_response(jsonify({'error': 'No last frame available'}), 404)

#-----------ERROR HANDLING--------------------

@app.errorhandler(404)
def not_found(error):
    logger.error("Page not found")
    return make_response(jsonify({'error': 'Not found'}), 404)

#-----------Helper Functions--------------------

def returnImg(BGRimg):
    retval, buffer = cv2.imencode('.png', BGRimg)
    response = make_response(buffer.tobytes())
    response.headers['Content-Type'] = 'image/png'
    return response

#this will never be called from production server routines! only works for python3 startserver.py
if __name__ == "__main__":
    #frameWorker.start(pipeline) #needs to be started before flask. since flask captures main process
    logger.info("Starting from main in startserver.py")
        
    app.run(host=cf['IP'], port=cf.getint('PORT'), debug=False)

