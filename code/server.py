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
    parser.add_option('-P', '--port-https', dest='httpsPort', help='port for https server. Default: 8081', default=8081, type="int")
    parser.add_option('-c', '--cache-directory', dest='cacheDir', help='directory for storing temporary files (cache). Default: cache', default='cache')
    parser.add_option('-s', '--cache-max-size', dest='cacheMaxSize', help='maximum size of temporary files (in KB). Note that actual disk usage may be higher in some special cases (high server load). Default: 100MB', default=100*1024, type="int")
    parser.add_option('-d', '--database', dest='database', help='database file to use (for storing users\' passwords. Default: users.db', default='users.db')
    options, args = parser.parse_args()
    config.httpPort = options.httpPort
    config.httpsPort = options.httpsPort
    config.cacheDir = options.cacheDir
    if config.cacheDir[-1] == '/':
        config.cacheDir = config.cacheDir[:-1]
    if not os.path.exists(config.cacheDir):
        os.makedirs(config.cacheDir)
    config.cacheMaxSize = options.cacheMaxSize*1024
    config.databaseFile = options.database

    http = threading.Thread(target=httpServer.start, args=(config.httpPort, False))
    http.daemon = True
    http.start()
    
    https = threading.Thread(target=httpServer.start, args=(config.httpsPort, True))
    https.daemon = True
    https.start()
    
    push= threading.Thread(target=hsConnection.startPushFileServer)
    push.daemon = True
    push.start()
    try:
        hsConnection.startHSServer()
    except KeyboardInterrupt:
        fileManager.removeCache()
        print("Shutting Down")
