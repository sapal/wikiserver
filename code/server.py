#!/usr/bin/env python
# coding=utf-8

import threading
from fileManager import fileManager
import httpServer
import hsConnection
import asyncore

if __name__=="__main__":
    http = threading.Thread(target=httpServer.start)
    http.daemon = True
    http.start()
    try:
        hsConnection.startHSServer()
    except KeyboardInterrupt:
        print("Shutting Down")
