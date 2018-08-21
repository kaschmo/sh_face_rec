# sh_face_rec - Smart Home Face Recognition
A simple face recognition system that can be used with any streaming camera and works with OpenHAB via REST communication. Runs on a Raspberry Pi.

![Animation](doc/images/animated_face_rec.gif?raw=true)
- Runs a small flask based http server that gets video streams from IP cameras on network and stores frames in a queue.
- Multiprocessing worker application process the video frames and run a face recognition procedure on each of the frames in pipeline
- Pipeline (details see below): 
    - Image Handling w/ OpenCV
    - Face Detection w/ MTCNN Tensorflow Implementation
    - Aligning/Cropping using dlib 
    - Face Embedding with dlib CNN 
    - Classification with scikit KNN 
- Once known faces are identified OpenHAB is notified via REST Interface call (requires REST API binding in OH)
- If only unknown faces are identified OpenHAB is notified via REST Interface call

Check the Wiki for detailed description of possible Face Detection/Recognition Frameworks incl. evaluation.
[Wiki](https://github.com/kaschmo/sh_face_rec/wiki/Framework-comparison)

## Face Processing Pipeline
![Processing Pipeline](doc/images/pipeline.png?raw=true)
This pipeline is heavily inspired by the [OpenFace Pipeline](https://github.com/cmusatyalab/openface).
See further down for information on training the neural networks of each pipeline step.
For basic image handling (reading/streaming, writing, transforming, extracing and showing) openCV is used.

### Face Detection
As a first step we need to detect any shapes in the video frames that look like faces. Luckily there are many frameworks available which can do that. The challenge is to find “good enough” performance for my usecase (640x480 blurry and dark camera feed) and balance with resource requirements = processing FPS (frames per second). See The [Wiki](https://github.com/kaschmo/sh_face_rec/wiki/Framework-comparison) for the framework evaluation. I went for an MTCNN implemetation of a face detector.
Implementation: davidsandberg's implementation of MTCNN for face detection [Github](https://github.com/davidsandberg/facenet/tree/master/src/align)


### Face Alignment and Crop
Once I have all boundary boxes around the faces in the frame I use dlibs pose predictor to align all the faces and crop them to a standard format of 64x64 pixels.
Implementation: Face Alignment and Landmark Extraction: dlib (pose_predictor 5point)

### Face Embedding
This step creates a 128bit representation (embeddings) of every face that can then be used by a classifier to determine if we have a match or not. I went for the [FaceNet](https://arxiv.org/abs/1503.03832) approach of using a pretrained Neural Network to create these face embeddings. 
See the [Wiki](https://github.com/kaschmo/sh_face_rec/wiki/Framework-comparison) for the frameworks that I evaluated.
I decided to use dlibs ResNet network to create 128bit vectors of the faces.
Implementation: dlib CNN face encoder [Dlib](http://dlib.net/cnn_face_detector.py.html). Comes with pretrained network on 3Mio face images from VGG and facescrub dataset.

### Face Classification
With the 128bit embeddings I can train a classifier to detect known faces. In this pipeline step every new detected face embedding is fed into the classifier to determine if we have a known face (threshold comparison) or not.
Implementation: knn classifier from sklearn

## Setup and Performance
The application is written to work on a Raspberry Pi3.
Python3 is required for multiprocessing. (Multithreading is terribly slow)
I used Anaconda as environment manager. Use the env.yml file in the root directory to set up an working Anaconda environment.
Configuration is pretty self-explanatory in confi.ini

Image/Video Handling is done with openCV, so any streaming IP camera or file system videos should work (not tested)
Performance with 640x480 videos (mjpg) on the RPi3:
- 3 FPS if no faces are in frame 
- 0.7 FPS with one face in frame
- 0.4 FPS with 2 faces in frame

![Setup Pis](doc/images/setup.png?raw=true)


### Repository Folder Structure
- sh_face_rec: contains all the code
    - align folder: mtcnn detector code (from facenet)
    - config.ini: all config data for application
    - logging.conf: logging configuration
    - startserver.py is the main
- models: contains pre-trained models for CNN and classifier models (need to be downloaded. links below.)
- test: contains unit test for components and visual debugging testcases for whole application
- testing_data: contains videos/images for testing
- training_data: contains labeled faces for training classifier
- openHAB: example code for openHAB integration

## Startup
### Preparation
- Configuration: all config settings need to be done in config.ini. (use config_template.ini and rename)
- Download pre-trained models for detector, face recognition (see below)
- Train classifier on your target platform (due to cross-platform pickle issues)
- configure model names in config.ini
- configure uwsgi_start.ini
- run tests first

### Production (uWSGI Server)
- Although the application is working with flask's internal werkzeug debug server, I recommend using a production server such as uWSGI
- Face Recognition Server is started with 
`./start.sh` (requires uwsgi as production server)
- A new streaming and face recognition job can be started with
`curl -i -H "Content-Type: application/json" -X POST -d {'"URL":"CAM_URL", "Time": "10"}' SERVER_URL:SERVER_PORT/detectJSON`
- The whole http API is listed in startserver.py
- config-file for uwsgi server is uwsgi_start.ini. Other servers such as gunicorn, gevent do not work with multiprocessing. The attribute processes should be >2 since the application forks 2 additional processes to main.


## Training & Models
- The face recognition pipeline uses Neural Networks for the first 3 steps. If you do not want to train the networks your own, you need to download pretrained models for each of the pipeline steps. Models need to be placed in model_path folder.
- Configuration of which models to use is possible in facerecognizer.py Class Variables. 
- Default models: 
1. Face Detection: 3 models for the o,r,n CNN required. Download from [Facenet/Align Github](https://github.com/davidsandberg/facenet/tree/master/src/align)
2. Face Alignment: depending on selsection, 5point or 68point shape predictor required. Download from [dlib git](https://github.com/davisking/dlib-models)
3. Face Encoding: The dlib face recognition ResNet model is required. Download from [dlib git](https://github.com/davisking/dlib-models)
4. Face classification: A trained KNN classifier is required. Use trainclassifier.py script and manual to create model and place in model_path.

## Testing
For visual inspection of the pipeline the two testcases
- test_facerecognizer 
- test_classifier can be used.
Execution: `python -m unittest test.test_classifier``

### Test_Facerecognizer
- Operates on single image
- Loads image, runs all pipeline steps
- visualizes landmarks and bounding boxes
- shows each single face (known and unknowns) with distance and original size information
`python3 -m unittest test.test_facerecognizer`

### Test_Classifier
- Operates on video
- executes full recognition stack on video
- visualizes bounding boxes and detected names
- can write to file
`python3 -m unittest test.test_classifier`

# API Examples
The flask server API takes simple REST calls
I use Postman to debug the API and the application.
API calls in openHAB via restcall.

## Examples
New Streaming Job from CAM_URL for 10s on server SERVER_URL:PORT
`curl -i -H "Content-Type: application/json" -X POST -d {'"URL":"CAM_URL", "Time": "10"}' SERVER_URL:SERVER_PORT/detectJSON`

List Statistics 
`curl -i -H SERVER_URL:SERVER_PORT/getStats`

Get i Known Person
`curl -i -H SERVER_URL:SERVER_PORT/getKnown/<int:index>`

Get i Known Face
`curl -i -H SERVER_URL:SERVER_PORT/getKnownFace/<int:index>`

Get i Unknown Face
`curl -i -H SERVER_URL:SERVER_PORT/getUnknownFace/<int:index>`

Get last complete Frame
`curl -i -H SERVER_URL:SERVER_PORT/getLastFrame`