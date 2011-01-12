#!/usr/bin/env python
# coding=utf-8

import threading
from fileManager import fileManager
import httpServer
import hsConnection

if __name__=="__main__":
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
