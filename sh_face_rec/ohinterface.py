#Class to interact with the OH REST interface
import requests
import base64
import logging
from logging.config import fileConfig
import sys

import configparser

config = configparser.ConfigParser()
config.read('sh_face_rec/config.ini')
cf = config['OHINTERFACE']

class OHInterface:
    def __init__(self):
        self.OHIP = cf['OH_IP'] #storing IP address of OH server
        self.OHPort = cf['OH_PORT']
        self.timeout = cf.getint('OH_timeout')
        fileConfig('sh_face_rec/logging.conf')
        self.logger = logging.getLogger("OHInterface")
        #No Authentification required.
        #self.username = "test" 
        #self.password = "test"

    def getItemState(self, itemName):
        self.logger.error("Not Supported")

    def postCommand(self, item, state):
        url = 'http://%s:%s/rest/items/%s'%(self.OHIP, self.OHPort, item)
        self.logger.info("Posting: %s. State: %s",url, state)
        try:
            req = requests.post(url, data=state, headers=self.basic_header(), timeout=self.timeout)
        
            self.logger.info("Returned: %s", req.status_code)
            if req.status_code != '200':
                self.logger.error("Error while posting.") 
                req.raise_for_status()
            else:    
                return '200'
        except:# (requests.Timeout):
            self.logger.error("Error in contacting OH. Status not updated.: %s")
    
    def putStatus(self, item, state):
        url = 'http://%s:%s/rest/items/%s/state'%(self.OHIP, self.OHPort, item)
        self.logger.info("Putting: %s",url)

        req = requests.put(url, data=state, headers=self.basic_header())
        if req.status_code != '200': 
            self.logger.error("Error while putting.") 
           #req.raise_for_status()   
        return req.status_code

    def setPresent(self, name):        
        itemName = 'presenceVideo_%s' % name 
        itemState = 'ON' 
        return self.postCommand(itemName,itemState)       
        

    def basic_header(self):
        #self.auth = base64.encodestring('%s:%s'%(self.username, self.password)).replace('\n', '')
        return {
            #"Authorization" : "Basic %s" %self.auth,
            "Content-type": "text/plain",
            "Accept": "application/json"}

    def unknownAlert(self, unknownCount):
        self.logger.info("Alerting %d unknowns.",unknownCount)
        #alert unknown entry to OH
        ret = self.postCommand('presenceVideo_unknowns', str(unknownCount))
        
        return ret