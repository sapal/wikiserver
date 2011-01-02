# coding=utf-8

from fileManager import fileManager
import fileManager as fm
import threading
import asynchat, asyncore
import socket
from Queue import Queue
import base64
import random # dorota

class HiddenServerConnection(asynchat.async_chat):
    '''Klasa reprezentująca trwałe połączenie HiddenServera z Serverem'''
    dbg = True
    responses = ["OK", "OLD", "MYNAMEIS"]
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock)
        self.requestQueue = Queue()
        self.sendRequests = Queue()
        self.set_terminator("\r\n")
        self.data = []
        self.response = {}
        self.user = "" # dorota
        print self.user
        self.writeThread = threading.Thread(target=self.writeLoop)
        self.writeThread.daemon = True
        self.writeThread.start()

    def writeLoop(self):
        global fileManager
        while True:
            request = self.requestQueue.get()
            filename = (self.user+"/"+request['filename']).replace("/",".")
            if filename in fileManager.fileInfo:
                info = fileManager.fileInfo[filename]
            else:
                info = fm.FileInfo()
            request['modifyTime'] = info.modifyTime
            print(self.user+str(request))
            self.sendRequests.put((request, info))
            self.push("GET\n")
            self.push("filename:{filename}\nmodifyTime:{modifyTime}\nid:{id}\noriginalRequest:{0}\n".format(
                base64.b64encode(request['originalRequest']), **request) )

    def collect_incoming_data(self, data):
        #print "DATA: "+data
        self.data.append(data)

    def processResponse(self):
        global fileManager
        r = self.response
        self.response = {}
        if HiddenServerConnection.dbg:
            print(r)
        if r['response'] == "MYNAMEIS":
            self.user = r['username'].strip()
            fileManager.hiddenServerConnections[self.user] = self
            return
        else:
            request, info = self.sendRequests.get()
            fileManager.processResponse(request['id'], r, info)
            c = request['answerCondition']
            c.acquire()
            c.notify()
            c.release()

    def handle_error(self):
        pass

    def found_terminator(self):
        data = "".join(self.data)
        self.data = []
        if data.strip() == "":
            self.processResponse()
            return
        if data.strip() in HiddenServerConnection.responses:
            self.response['response'] = data.strip()
        else:
            colon = data.find(":")
            field = data[:colon].lower().strip()
            value = data[colon+1:]
            self.response[field] = value

    def handle_close(self):
        print "Close"
        self.close()

class HSServer(asyncore.dispatcher):
    '''Klasa odpowiedzialna za tworzenie HiddenServerConnectionów'''

    def __init__(self, port, reuseAddress=False):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuseAddress:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)
        self.myname = "hs" + str(random.randint(1, 1000000)) # dorota
        print "Hidden Server name is " + self.myname # dorota

    def handle_accept(self):
        p = self.accept()
        if not p:
            return
        conn, addr = p
        h = HiddenServerConnection(conn)
       
        
def startHSServer():
    s = HSServer(8888, reuseAddress=True) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    print("Starring HSServer.")
    asyncore.loop()

class PushFileConnection(asynchat.async_chat):
    '''Klasa reprezentująca połączenie przesyłające plik z HiddenServera do Servera.
Zapisuje dane do odpowiedniego pliku i przy każdym zapisie wywołuje sizeChanged()'''
    dbg = True
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock)
        self.BUFFER_SIZE = 10
        self.set_terminator("\n")
        self.data = []
        self.header = {}
        self.reciveData = False
        self.recived = 0
        self.file = None
        self.fileInfo = None

    def collect_incoming_data(self, data):
        self.data.append(data)

    def handle_error(self):
        import traceback
        traceback.print_exc()


    def formatHeader(self):
        for key in ('length','id'):
            self.header[key] = int(self.header[key])
        self.header['filetype'] = self.header['filetype'].strip()
        if PushFileConnection.dbg:
            print self.header
    @property
    def length(self):
        return self.header['length']

    def found_terminator(self):
        global fileManager
        data = "".join(self.data)
        self.data = []
        if self.reciveData:
            self.recived += len(data)
            self.file.write(data)
            self.file.flush()
            self.fileInfo.sizeChanged(self.recived)
            self.set_terminator(min(self.BUFFER_SIZE,self.length - self.recived))
            return
        colon = data.find(':')
        field = data[:colon].lower().strip()
        value = data[colon+1:]
        if field == "":
            self.formatHeader()
            self.set_terminator(min(self.BUFFER_SIZE,self.length - self.recived))
            self.fileInfo = fileManager.requestInfo[self.header['id']]
            self.fileInfo.fileType = self.header['filetype']
            self.fileInfo.size = self.header['length']
            self.file = open(self.fileInfo.filename, 'w')
            self.reciveData = True
        else:
            self.header[field] = value

    def handle_close(self):
        if PushFileConnection.dbg:print "PFC:Close"
        self.close()
        
class PushFileServer(asyncore.dispatcher):
    '''Klasa odpowiedzialna za tworzenie PushFileConnectionów'''

    def __init__(self, port, reuseAddress=False):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuseAddress:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)

    def handle_accept(self):
        p = self.accept()
        if not p:
            return
        conn, addr = p
        PushFileConnection(conn)
        
def startPushFileServer():
    print("Starting PushFileServer")
    s = PushFileServer(9999, reuseAddress=True) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    asyncore.loop()
