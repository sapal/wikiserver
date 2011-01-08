#!/usr/bin/env python
# coding=utf-8

import random   
import asyncore, socket	
from helper import parseData
import os
import threading

def done_fun():
    print 'byebye'

class HiddenServer(asyncore.dispatcher):
    def __init__(self, host, path, myname):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.path = path
        self.connect( (host, 8888))
        self.myname = myname
        print "Hello. My name is " + self.myname
        self.buffer = 'MYNAMEIS\nusername:' + self.myname + '\n\n'
        # print 'MYNAMEIS:' + self.myname + '\r\n'
        self.data = []
    def handle_connect(self):
        pass
    def handle_close(self):
        done_fun()
        self.close()
    def handle_read(self):
        got = self.recv(8192)
        self.data.append(got)
        if got.find('\r\n') != -1:
            self.processRequest()
    def writable(self):
        return (len(self.buffer) > 0)
    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]
    def processRequest(self):
        request = "".join(self.data)
        self.data = []
        terminator = request.find('\r\n')
        self.data.append(request[terminator+2:])
        request = request[:terminator]
        self.req = parseData(request)
        print self.req
        if(self.req['response'] == 'GET'):
            self.answerToGet()
    def answerToGet(self):
        filename = self.req['filename']
        if(filename == '/'):
            print 'ls of main catalogue'
            self.answerToLsMain()
            return
        filename = filename[1:]
        print 'filename ' + filename
        if os.path.exists(filename) == False:
            print 'No such path'
            self.answerToNope()
            return
        print 'Ok path'
        if(os.path.isfile(filename)):
            self.answerToFile(filename)
            return
        if(os.path.isdir(filename)):
            self.answerToDir(filename)
            return
            
        # TODO
    def answerToNope(self):
        self.buffer += 'NOPE\nid:' + self.req['id'] + '\n\n'
    def answerToLsMain(self):
        # TODO
        print 'main ls'
        pass
    def answerToFile(self, filename):
        print 'its a file'
        if('date' in self.req):
            if(self.req['data'] + 100 < str(os.path.getmtime(filename))):
                self.buffer += 'OK\nid:' + self.req['id'] + '\n\n'
                return
        self.buffer += 'OLD\nid:' + self.req['id'] + '\nsize:'
        self.buffer += str(os.path.getsize(filename)) + '\n'
        self.buffer += 'type:file\n\n'
        print 'new thread?'
        newThreadPushFile(self.host, filename, 'file', self.req['id'])
    def answerToDir(self, filename):
        print 'get dir'
        pass

class PushFileConnectionClient(asyncore.dispatcher):
    def __init__(self, host, filename, typ, id):
        print 'hello init'
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, 9999))
        self.buffer = ""
        self.filename = filename
        self.id = id
        self.typ = typ
        if(self.typ == 'file'):
            self.sendFile()
        else:
            self.sendDir()    
    def handle_connect(self):
        pass
    def handle_close(self):
        self.close()
    def handle_read(self):
        self.recv(8192)
    def writable(self):
        return (len(self.buffer) > 0)
    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]
    def sendFile(self):
        self.buffer += 'PUSH\n'
        self.buffer += 'id:'+self.id+'\n'
        self.buffer += 'size:' + str(os.path.getsize(self.filename)) + '\n'
        self.buffer += 'filename:' + self.filename + '\n'
        self.buffer += 'type' + self.typ + '\n\n'
        f = open(self.filename, "rb")
        data = f.read()
        self.buffer += data
class HelperClass:
    def __init__(self, host, filename, typ, id):
        self.host = host
        self.filename = filename
        self.typ = typ
        self.id = id
    def startAndPushFile(self):
        PushFileConnectionClient(self.host, self.filename, self.typ, self.id)
        
def newThreadPushFile(host, filename, typ, id):
    hc = HelperClass(host, filename, typ, id)
    pfc = threading.Thread(target=hc.startAndPushFile)
    pfc.deamon = True
    pfc.start()
    print 'launched'
    
client = HiddenServer('localhost', '/', 'servuś')
asyncore.loop()
