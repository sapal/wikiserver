# coding=utf-8

from fileManager import fileManager
#import fileManager as fm
import threading
import asynchat, asyncore
import socket
from Queue import Queue
from helper import parseData
import base64
from logging import basicConfig, debug, DEBUG
#basicConfig(filename='hsConnection.log', level=DEBUG, filemode='w')
#def debug(x):
#    print(x)

class HiddenServerConnection(asynchat.async_chat):
    '''Klasa reprezentująca trwałe połączenie HiddenServera z Serverem'''
    responses = ["OK", "OLD", "MYNAMEIS"]
    def __init__(self, sock, map=None):
        self.buffer = ""
        asynchat.async_chat.__init__(self, sock, map=map)
        self.requestQueue = Queue()
        self.sentRequests = Queue()
        self.set_terminator("\n\n")
        self.data = []
        self.response = {}
        self.user = "" 
        self.stopLock = threading.RLock() # tego locka trzeba zdobyć, żeby zakończyć HiddenServerConnection
        self.writeThread = threading.Thread(target=self.writeLoop)
        self.writeThread.daemon = True
        self.writeThread.start()

    def writeLoop(self):
        """Funkcja przekazująca wszystkie zapytania z requestQueue do HiddenServera.
        Uruchamiana na osobnym wątku."""
        global fileManager
        while True:
            request = self.requestQueue.get()
            debug("GOT REQUEST:"+request['filename'])
            path = self.user + request['filename']
            with self.stopLock:
                info = fileManager.startUsingFileInfo(path)
                request['modifyTime'] = info.modifyTime
                debug('REQUEST: '+self.user+' '+str(request))
                self.sentRequests.put((request, info))
            self.buffer += "GET\nfilename:{filename}\nmodifyTime:{modifyTime}\nid:{id}\noriginalRequest:{0}\n\n".format(
                base64.b64encode(request['originalRequest']), **request) 
            while len(self.buffer)>0:
                sent = self.send(self.buffer)
                self.buffer = self.buffer[sent:]
            debug("REQUEST SENT")

    def collect_incoming_data(self, data):
        #debug("INCOMING DATA: "+data)
        self.data.append(data)

    def processResponse(self):
        """Funkcja przetwarzająca odpowiedź od HiddenServera."""
        #debug('processRespone')
        global fileManager
        r = self.response
        self.response = {}
        #debug(str(r))
        #debug('to byl debug')
        if r['response'] == "MYNAMEIS":
            #debug('mynameis')
            self.user = r['username'].strip()
            fileManager.hiddenServerConnections[self.user] = self
            self.push('Hello ' + r['username'].strip() + ' i am your master\n\n')
            #debug('Got him!')
            return
        else:
            #debug('else czyli nie mynameis')
            with self.stopLock:
                request, info = self.sentRequests.get()
                fileManager.processResponse(request['id'], r, info)
                c = request['answerCondition']
                with c:
                    c.notify()
                info.stopUsing()
        #debug('endof')    

    def handle_error(self):
        debug("HSC:ERROR")
        #self.handle_close()

    def found_terminator(self):
        data = "".join(self.data)
        self.data = []
        self.response = parseData(data)
        self.processResponse()   # dorota 

    def handle_close(self):
        with self.stopLock:
            debug("Close")
            self.close()
            while not self.sentRequests.empty():
                r,info = self.sentRequests.get(False)
                info.stopUsing()
            if self.user != "":
                del fileManager.hiddenServerConnections[self.user]


class HSServer(asyncore.dispatcher):
    '''Klasa odpowiedzialna za tworzenie HiddenServerConnectionów'''

    def __init__(self, port, reuseAddress=False, map=None):
        asyncore.dispatcher.__init__(self, None, map)
        self.map = map
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuseAddress:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)

    def handle_accept(self):
        print("ACCEPT")
        p = self.accept()
        if not p:
            return
        conn, addr = p
        HiddenServerConnection(conn, self.map)
        
def startHSServer():
    m = {}
    HSServer(8888, reuseAddress=True, map=m) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    print("Starting HSServer.")
    asyncore.loop(map=m)

class PushFileConnection(asynchat.async_chat):
    '''Klasa reprezentująca połączenie przesyłające plik z HiddenServera do Servera.
Zapisuje dane do odpowiedniego pliku i przy każdym zapisie wywołuje sizeChanged()'''
    ac_in_buffer_size = 32*1024
    def __init__(self, sock, map=None):
        asynchat.async_chat.__init__(self, sock=sock, map=map)
        self.BUFFER_SIZE = 16*1024
        self.set_terminator("\n\n")
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
        debug(traceback.format_exc())

    def formatHeader(self):
        """Sformatuj nagłówek (zamień stringi w self.header na odpowiednie
        typy."""
        try:
            for key in ('size','id'):
                self.header[key] = int(self.header[key])
            self.header['type'] = self.header['type'].strip()
        except BaseException as e:
            print(e)
            print(str(self.header))
        #debug(str(self.header))

    @property
    def length(self):
        return self.header['size']

    def found_terminator(self):
        global fileManager
        data = "".join(self.data)
        self.data = []
        if self.reciveData:
            self.recived += len(data)
            #debug("TERMINATOR: " +str(self.recived))
            self.file.write(data)
            self.file.flush()
            self.fileInfo.sizeChanged(self.recived)
            if self.length == self.recived:
                debug("OK")
                #self.handle_close()
                return
            term = min(self.BUFFER_SIZE,self.length - self.recived)
            self.set_terminator(term)
            #debug("New terminator: " +str(term) + str((self.recived, self.length)))
            return
        self.header = parseData(data)
        self.formatHeader()
        self.fileInfo = fileManager.requestInfo[self.header['id']]
        self.fileInfo.fileType = self.header['type']
        self.fileInfo.size = self.header['size']
        self.file = open(self.fileInfo.filename, 'w')
        self.reciveData = True
        if self.length != 0:
            self.set_terminator(min(self.BUFFER_SIZE,self.length - self.recived))
        else:
            self.fileInfo.sizeChanged(0)

    def handle_close(self):
        debug("PFC:Close")
        self.close()
        
class PushFileServer(asyncore.dispatcher):
    '''Klasa odpowiedzialna za tworzenie PushFileConnectionów'''

    def __init__(self, port, reuseAddress=True, map=None):
        asyncore.dispatcher.__init__(self, map=map)
        self.map = map
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
        PushFileConnection(conn, map=self.map)
        
def startPushFileServer():
    print("Starting PushFileServer")
    m = {}
    PushFileServer(9999, reuseAddress=True, map=m) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    asyncore.loop(map=m)
