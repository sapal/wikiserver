#!/usr/bin/env python
# coding=utf-8

import random   
import asyncore, socket	
import asynchat
from helper import parseData
import os
import threading
import datetime
import time
from optparse import OptionParser

def done_fun():
    print 'byebye'

class HiddenServer(asynchat.async_chat):
    def __init__(self, host, path, myname):
        self.buffer = ""
        asynchat.async_chat.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.path = path
        if(path[-1] != '/'):
            path = path + '/'
        self.connect( (host, 8888))
        self.myname = myname
        print "Hello. Thanks for using WikiServer. You are now known as " + self.myname + "."
        self.buffer = 'MYNAMEIS\nusername:' + self.myname + '\n\n'
        # print 'MYNAMEIS:' + self.myname + '\r\n'
        self.data = []
        self.set_terminator('\n\n')
    def collect_incoming_data(self, data):
        self.data.append(data)
    def handle_connect(self):
        pass
    def handle_close(self):
        done_fun()
        self.close()
    def writable(self):
        return (len(self.buffer) > 0)
    def handle_write(self):
        sent = self.send(self.buffer)
        print "\tSending info."
        # print("HS: sent:"+str(self.buffer[:sent]))
        self.buffer = self.buffer[sent:]
    def found_terminator(self):
        self.processRequest()
    def processRequest(self):
        request = "".join(self.data)
        self.data = []
        self.req = parseData(request)
        #print self.req
        if(self.req['response'] == 'GET'):
            self.answerToGet()
    def answerToGet(self):
        filename = self.req['filename']
        if(filename[0] == '/'):
            filename = filename[1:]
        if(self.path != '/'):
            filename = self.path + filename
        print 'New filename is ' + filename + ' (empty if this directory)'
        if(filename == ''):
            print 'Responding to ls of this directory'
            self.answerToLsMain()
            return
        #filename = filename[1:]
        print 'Responding to request of "' + filename + '"'
        if not os.path.exists(filename):
            print '\tNo such path'
            self.answerToNope()
            return
        print '\tOk path'
        if(os.path.isfile(filename)):
            self.answerToFile(filename, filename, 'file')
            return
        if(os.path.isdir(filename)):
            self.answerToDir(filename)
            return
            
    def answerToNope(self):
        self.buffer += 'NOPE\nid:' + self.req['id'] + '\n\n'
    def answerToLsMain(self):
        tmpfile = 'hiddenServerWorkingFile' + str(random.randint(10000, 1000000)) + str(datetime.datetime.now())
        tmpfile = '/tmp/' + tmpfile
        print "debug - tmpfile is : " + tmpfile
        f = open(tmpfile, "w")
        for line in os.listdir("."):
            f.write(line + "\n")
        f.close()                
        self.answerToFile(tmpfile, '/', 'directory')
        # usuwane w PushFileConnection - po przeslaniu
    def answerToFile(self, filename, fakeFilename, typ):
        if(typ == 'file'):
            print '\tIt is a file.'
        else:
            print '\tIt is a directory.'
        if('date' in self.req):
            print '\t\tGot a file with a date'
            if(self.req['date'] > os.path.getmtime(filename)):
                self.buffer += 'OK\nid:' + self.req['id'] + '\n\n'
                print "\t\tDate is OK"
                return
        self.buffer += 'OLD\nid:' + self.req['id'] + '\nsize:'
        self.buffer += str(os.path.getsize(filename)) + '\n'
        self.buffer += 'type:file\n'
        self.buffer += 'modifytime:0\n\n' #TODO:zrobić
        newThreadPushFile(self.host, filename, fakeFilename, typ, self.req['id'])
    def answerToDir(self, filename):
        tmpfile = 'hiddenServerWorkingFile' + str(random.randint(10000, 1000000)) + str(datetime.datetime.now())
        tmpfile = '/tmp/' + tmpfile
        f = open(tmpfile, "w")
        for line in os.listdir(filename):
            f.write(line + "\n")
        f.close()                
        self.answerToFile(tmpfile, filename, 'directory')
        # usuwane w PushFileConnection - po przeslaniu

class PushFileConnectionClient(socket.socket):
    def __init__(self, host, filename, fakeFilename, typ, id):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        #print 'hello init'
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
            # print(sent)

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
        print("\tFile sent.")
        
def newThreadPushFile(host, filename, fakeFilename, typ, id):
    pfc = PushFileConnectionClient(host, filename, fakeFilename, typ, id)

    pfcThread = threading.Thread(target=pfc.sendFile)
    pfcThread.deamon = True
    pfcThread.start()
    #print 'launched'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--host', dest='host', help='host to connect to, default is localhost')
    parser.add_option('-n', '--name', dest='hidden_server_name', help='name of your hidden server, default is servus')
    parser.add_option('-d', '--dir', dest='directory', help='the directory you want to share')
    (options, args) = parser.parse_args()
    host = 'localhost'
    if(options.host!=None):
        host = options.host    
    #name = 'servuś'
    directory = '/'
    if(options.directory!=None):
        directory = options.directory
    if(options.hidden_server_name!=None):
        name = options.hidden_server_name
        client = HiddenServer(host, directory, name)
        asyncore.loop()
    else:
        print 'Brak nazwy serwera. Podaj z opcja -n albo --name. Więcej opcji: -h.'
