#!/usr/bin/env python
# coding=utf-8

import random   
import asyncore, socket	
from helper import parseData
import os
import threading
import datetime
import time
from optparse import OptionParser

def done_fun():
    print 'byebye'

class HiddenServer(asyncore.dispatcher):
    def __init__(self, host, path, myname):
        self.buffer = ""
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
        print(self.data)
        if (got.find('\n\n') != -1 or (len(self.data) > 0 and self.data[-1][-1] == '\n' and got[0] == '\n')):
            self.processRequest()
    def writable(self):
        return (len(self.buffer) > 0)
    def handle_write(self):
        sent = self.send(self.buffer)
        print("HS: sent:"+str(self.buffer[:sent]))
        self.buffer = self.buffer[sent:]
    def processRequest(self):
        request = "".join(self.data)
        self.data = []
        terminator = request.find('\n\n')
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
            self.answerToFile(filename, filename, 'file')
            return
        if(os.path.isdir(filename)):
            self.answerToDir(filename)
            return
            
    def answerToNope(self):
        self.buffer += 'NOPE\nid:' + self.req['id'] + '\n\n'
    def answerToLsMain(self):
        # TODO
        print 'main ls'
        tmpfile = 'hiddenServerWorkingFile' + str(random.randint(10000, 1000000)) + str(datetime.datetime.now())
        print tmpfile
        f = open(tmpfile, "w")
        for line in os.listdir("."):
            f.write(line + "\n")
        f.close()                
        self.answerToFile(tmpfile, '/', 'directory')
        # usuwane w PushFileConnection - po przeslaniu
    def answerToFile(self, filename, fakeFilename, typ):
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
        newThreadPushFile(self.host, filename, fakeFilename, typ, self.req['id'])
    def answerToDir(self, filename):
        print 'get dir'
        tmpfile = 'hiddenServerWorkingFile' + str(random.randint(10000, 1000000)) + str(datetime.datetime.now())
        f = open(tmpfile, "w")
        for line in os.listdir(filename):
            f.write(line + "\n")
        f.close()                
        self.answerToFile(tmpfile, filename, 'directory')
        # usuwane w PushFileConnection - po przeslaniu

class PushFileConnectionClient(socket.socket):
    def __init__(self, host, filename, fakeFilename, typ, id):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        print 'hello init'
        self.connect( (host, 9999))
        self.buffer = ""
        self.filename = filename
        self.fakeFilename = filename
        self.id = id
        self.typ = typ

    def sendBuffer(self):
        while len(self.buffer)>0:
            sent = self.send(self.buffer)
            self.buffer = self.buffer[sent:]
            print(sent)

    def sendFile(self):
        self.buffer += 'PUSH\n'
        self.buffer += 'id:'+self.id+'\n'
        self.buffer += 'size:' + str(os.path.getsize(self.filename)) + '\n'
        self.buffer += 'filename:' + self.fakeFilename + '\n'
        self.buffer += 'type:' + self.typ + '\n'
        self.buffer += 'modifytime:0\n\n' #TODO:zrobić
        self.sendBuffer()
        f = open(self.filename, "rb")
        data = f.read()
        self.buffer += data
        self.sendBuffer()
        self.close()
        if(self.typ == 'directory'):
            os.remove(self.filename)
        print("SENT")
        
def newThreadPushFile(host, filename, fakeFilename, typ, id):
    pfc = PushFileConnectionClient(host, filename, fakeFilename, typ, id)

    pfcThread = threading.Thread(target=pfc.sendFile)
    pfcThread.deamon = True
    pfcThread.start()
    print 'launched'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--host', dest='host', help='host to connect to, default is localhost')
    parser.add_option('-n', '--name', dest='hidden_server_name', help='name of your hidden server, default is servus')
    (options, args) = parser.parse_args()
    print options
    print args
    host = 'localhost'
    if(options.host!=None):
        host = options.host
    name = 'servuś'
    if(options.hidden_server_name!=None):
        name = options.hidden_server_name
    print 'host: ' + host + ' myname: ' + name    
    client = HiddenServer(host, '/', name)
    asyncore.loop()
