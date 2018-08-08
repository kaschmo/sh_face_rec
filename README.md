# sh_face_rec - Smart Home Face Recognition
A simple face recognition system that can be used with any streaming camera and works with OpenHAB via REST communication. Runs on a Raspberry Pi.
- Runs a small flask based http server that gets video streams from IP cameras on network and stores frames in a queue.
- Multiprocessing worker application process the video frames and run a face recognition procedure on each of the frames in pipeline
- Pipeline (see below): 
    - Image Handling w/ OpenCV
    - Face Detection w/ MTCNN Tensorflow Implementation
    - Aligning/Cropping using dlib 
    - embedding with dlib CNN 
    - classification with KNN 
- Once known faces are identified OpenHAB is notified via REST Interface call (requires REST API binding in OH)
- If only unknown faces are identified OpenHAB is notified via REST Interface call

Check the Wiki for detailed description of possible Face Detection/Recognition Frameworks incl. evaluation.
[Wiki](https://github.com/kaschmo/sh_face_rec/wiki/Framework-comparison)

![Processing Pipeline](doc/images/pipeline.png?raw=true)


## Setup and Performance
The application is written to work on a Raspberry Pi3.
Python3 is required.
I used Anaconda as environment manager. Use the env.yml file in the root directory to set up an working Anaconda environment.
Configuration is pretty self-explanatory in confi.ini

Image/Video Handling is done with openCV, so any streaming IP camera or file system videos should work (not tested)
Performance with 640x480 videos (mjpg) on the RPi3:
- 3 FPS if no faces are in frame 
- 0.7 FPS with one face in frame
- 0.4 FPS with 2 faces in frame

![Setup Pis](doc/images/setup.png?raw=true)


### Folder Structure
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

## Startup and API
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

## Face Recognition Pipeline
The Face Recognition Pipeline performs the following 4 steps with the listed frameworks/tools being used
1. Face Detection: davidsandberg's implementation of MTCNN for face detection [Github](https://github.com/davidsandberg/facenet/tree/master/src/align)
2. Face Alignment and Landmark Extraction: dlib (pose_predictor 5point)
3. Face Encoding (creating 128D encoding of face): dlib CNN face encoder [Dlib] (http://dlib.net/cnn_face_detector.py.html)
4. Face classification: knn classifier from sklearn

For image handling (reading, writing, transforming, extracing and showing) openCV is used.

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
