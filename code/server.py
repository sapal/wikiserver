#!/usr/bin/env python
# coding=utf-8

import threading
from fileManager import fileManager
import httpServer
import hsConnection
from optparse import OptionParser
import config
import os

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option('-p', '--port', dest='httpPort', help='port for http server. Default: 8080', default=8080, type="int")
    parser.add_option('-c', '--cache-directory', dest='cacheDir', help='directory for storing temporary files (cache). Default: cache', default='cache')
    parser.add_option('-s', '--cache-max-size', dest='cacheMaxSize', help='maximum size of temporary files (in KB). Note that actual disk usage may be higher in some special cases (high server load). Default: 100MB', default=100*1024, type="int")
    options, args = parser.parse_args()
    config.httpPort = options.httpPort
    config.cacheDir = options.cacheDir
    if config.cacheDir[-1] == '/':
        config.cacheDir = config.cacheDir[:-1]
    if not os.path.exists(config.cacheDir):
        os.makedirs(config.cacheDir)
    config.cacheMaxSize = options.cacheMaxSize*1024

    http = threading.Thread(target=httpServer.start)
    http.daemon = True
    http.start()
    push= threading.Thread(target=hsConnection.startPushFileServer)
    push.daemon = True
    push.start()
    try:
        hsConnection.startHSServer()
    except KeyboardInterrupt:
        fileManager.removeCache()
        print("Shutting Down")
