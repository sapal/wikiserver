# coding=utf-8

import random
import asyncore, socket

def done_fun():
    print 'byebye'

class HiddenServer(asyncore.dispatcher):
    def __init__(self, host, path, myname):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, 8888))
        self.myname = myname
        print "Hello. My name is " + self.myname
        self.buffer = 'MYNAMEIS:' + self.myname + '\r\n'
        # print 'MYNAMEIS:' + self.myname + '\r\n'
    def handle_connect(self):
        pass
    def handle_close(self):
        done_fun()
        self.close()
    def hanlde_read(self):
        print self.recv(8192)
    def writable(self):
        return (len(self.buffer) > 0)
    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

client = HiddenServer('localhost', '/', 'servus')
asyncore.loop()
