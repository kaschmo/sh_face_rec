from flask import Flask, make_response, request, abort,jsonify, send_file
import sys
import cv2
import time
from videopipeline import VideoPipeline
from frameworker import FrameWorker
from frame import Frame
from downloader import Downloader
import configparser

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['STARTSERVER']

pipeline = VideoPipeline()
frameWorker = FrameWorker()
downloader = Downloader()

frameWorker.start(pipeline) #needs to be started before flask. since flask captures main process
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
    if pipeline.isStreaming:
        return jsonify("Error: only one stream allowed"),400
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
    #TODO detecte today, image_size, 
    
    if frameWorker.presenceDetector.getKnownCount() > 0:
        lastKnownFace = frameWorker.presenceDetector.getLastKnown()
        lastKnownFaceName = lastKnownFace.name
        lastKnownFaceTime = lastKnownFace.getCTime()
    else:
        lastKnownFaceName = "none"
        lastKnownFaceTime = 0
    
    
    if frameWorker.presenceDetector.getUnknownCount() > 0:
        lastUnknownFace = frameWorker.presenceDetector.getLastUnknown()
        lastUnknownFaceTime = lastUnknownFace.getCTime()
    else:
        lastUnknownFaceTime = 0

    return jsonify(pipelineLength = pipeline.Q.qsize(),
                    streamingFPS = pipeline.streamingFPS,
                    lastRun = pipeline.getLastRun(),
                    isStreaming = pipeline.isStreaming,
                    workerIdle = frameWorker.idle,
                    processingFPS = frameWorker.workingFPS,
                    knownCount = frameWorker.presenceDetector.getKnownCount(),
                    unknownCount = frameWorker.presenceDetector.getUnknownCount(),
                    lastKnownName = lastKnownFaceName,
                    lastKnownTime = lastKnownFaceTime,
                    lastUnknownTime = lastUnknownFaceTime),200

@app.route('/getKnownCount')
def getKnownCount():
    return jsonify(knownCount = frameWorker.presenceDetector.getKnownCount()),200

@app.route('/getUnknownCount')
def getUnknownCount():
    return jsonify(unknownCount = frameWorker.presenceDetector.getUnknownCount()),200

###---------------KNOWN ACCESS----------------

@app.route('/getKnown/<int:index>')
def getKnown(index):
    if index == -1:
        #get last Face
        index = frameWorker.presenceDetector.getKnownCount()-1

    if frameWorker.presenceDetector.getKnownCount() > index: 
        KnownFace = frameWorker.presenceDetector.getKnownFromList(index)
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
        index = frameWorker.presenceDetector.getKnownCount()-1
    if frameWorker.presenceDetector.getKnownCount() > index: 
        lastFace = frameWorker.presenceDetector.getKnownFromList(index).getBGR()
        return returnImg(lastFace),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)


###---------------UNKNOWN ACCESS----------------

@app.route('/getUnknown/<int:index>')
def getUnknown(index):
    if index == -1:
        #get last UnknownFace
        index = frameWorker.presenceDetector.getUnknownCount()-1

    if frameWorker.presenceDetector.getUnknownCount() > index:
        UnknownFace = frameWorker.presenceDetector.getUnknownFromList(index)
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
        index = frameWorker.presenceDetector.getUnknownCount()-1
    if frameWorker.presenceDetector.getUnknownCount() > index: 
        lastFace = frameWorker.presenceDetector.getUnknownFromList(index).getBGR()
        return returnImg(lastFace),200
    else:
        return make_response(jsonify({'error': 'Index out of range'}), 404)

#-----------FRAME ACCESS--------------------

@app.route('/getLastFrame')
def getLastFrame():
    if frameWorker.lastFrame != None: 
        return returnImg(frameWorker.lastFrame.getBGR()),200
    else:
        return make_response(jsonify({'error': 'No last frame available'}), 404)

#-----------ERROR HANDLING--------------------

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

#-----------Helper Functions--------------------

def returnImg(BGRimg):
    retval, buffer = cv2.imencode('.png', BGRimg)
    response = make_response(buffer.tobytes())
    response.headers['Content-Type'] = 'image/png'
    return response


if __name__ == "__main__":
    #frameWorker.start(pipeline) #needs to be started before flask. since flask captures main process
    print("Starting from main in startserver.py")
    #app.run(host='192.168.1.25', port=5001, debug=False)
    app.run(host=cf['IP'], port=cf.getint('PORT'), debug=False)


#further API ideas
#- stopstreaming
#- getStatus: working, streaming
#- getLastFrame