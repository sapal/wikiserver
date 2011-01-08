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
        self.buffer += 'type:file\n'
        self.buffer += 'modifytime:0\n\n' #TODO:zrobić
        print 'new thread?'
        newThreadPushFile(self.host, filename, 'file', self.req['id'])
    def answerToDir(self, filename):
        print 'get dir'
        pass

class PushFileConnectionClient(socket.socket):
    def __init__(self, host, filename, typ, id):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        print 'hello init'
        self.connect( (host, 9999))
        self.buffer = ""
        self.filename = filename
        self.id = id
        self.typ = typ

    def sendData(self):
        if(self.typ == 'file'):
            self.sendFile()
        else:
            self.sendDir()    

    def sendBuffer(self):
        while len(self.buffer)>0:
            sent = self.send(self.buffer)
            self.buffer = self.buffer[sent:]
            print(sent)

    def sendFile(self):
        self.buffer += 'PUSH\n'
        self.buffer += 'id:'+self.id+'\n'
        self.buffer += 'size:' + str(os.path.getsize(self.filename)) + '\n'
        self.buffer += 'filename:' + self.filename + '\n'
        self.buffer += 'type:' + self.typ + '\n'
        self.buffer += 'modifytime:0\n\n' #TODO:zrobić
        f = open(self.filename, "rb")
        data = f.read()
        self.buffer += data
        self.sendBuffer()
        print("SENDED")
        
def newThreadPushFile(host, filename, typ, id):
    pfc = PushFileConnectionClient(host, filename, typ, id)

    pfcThread = threading.Thread(target=pfc.sendData)
    pfcThread.deamon = True
    pfcThread.start()
    print 'launched'
    
client = HiddenServer('localhost', '/', 'servuś')
asyncore.loop()
