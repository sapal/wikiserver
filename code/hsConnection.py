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
basicConfig(filename='hsConnection.log', level=DEBUG, filemode='w')

class HiddenServerConnection(asynchat.async_chat):
    '''Klasa reprezentująca trwałe połączenie HiddenServera z Serverem'''
    responses = ["OK", "OLD", "MYNAMEIS"]
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock)
        self.requestQueue = Queue()
        self.sendRequests = Queue()
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
            debug("GOT REQUEST")
            filename = fileManager.getFilename(request['filename'], user=self.user, id=request['id'])
            with self.stopLock:
                info = fileManager.startUsingFileInfo(filename)
                request['modifyTime'] = info.modifyTime
                debug('REQUEST: '+self.user+' '+str(request))
                self.sendRequests.put((request, info))
            self.push("GET\n")
            self.push("filename:{filename}\nmodifyTime:{modifyTime}\nid:{id}\noriginalRequest:{0}\r\n".format(
                base64.b64encode(request['originalRequest']), **request) )

    def collect_incoming_data(self, data):
        #debug("INCOMING DATA: "+data)
        self.data.append(data)

    def processResponse(self):
        """Funkcja przetwarzająca odpowiedź od HiddenServera."""
        debug('processRespone')
        global fileManager
        r = self.response
        self.response = {}
        debug(str(r))
        debug('to byl debug')
        if r['response'] == "MYNAMEIS":
            debug('mynameis')
            self.user = r['username'].strip()
            fileManager.hiddenServerConnections[self.user] = self
            self.push('Hello ' + r['username'].strip() + ' i am your master\r\n')
            debug('Got him!')
            return
        else:
            debug('else czyli nie mynameis')
            with self.stopLock:
                request, info = self.sendRequests.get()
                fileManager.processResponse(request['id'], r, info)
                c = request['answerCondition']
                with c:
                    c.notify()
                info.stopUsing()
        debug('endof')    

    def handle_error(self):
        pass

    def found_terminator(self):
        data = "".join(self.data)
        self.data = []
        self.response = parseData(data)
        self.processResponse()   # dorota 

    def handle_close(self):
        with self.stopLock:
            debug("Close")
            self.close()
            while not self.sendRequests.empty():
                r,info = self.sendRequests.get(False)
                info.stopUsing()

class HSServer(asyncore.dispatcher):
    '''Klasa odpowiedzialna za tworzenie HiddenServerConnectionów'''

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
        HiddenServerConnection(conn)
        
def startHSServer():
    HSServer(8888, reuseAddress=True) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    print("Starting HSServer.")
    asyncore.loop()

class PushFileConnection(asynchat.async_chat):
    '''Klasa reprezentująca połączenie przesyłające plik z HiddenServera do Servera.
Zapisuje dane do odpowiedniego pliku i przy każdym zapisie wywołuje sizeChanged()'''
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock)
        self.BUFFER_SIZE = 10
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
        for key in ('length','id'):
            self.header[key] = int(self.header[key])
        self.header['filetype'] = self.header['filetype'].strip()
        debug(str(self.header))

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
        self.header = parseData(data)
        self.formatHeader()
        self.set_terminator(min(self.BUFFER_SIZE,self.length - self.recived))
        self.fileInfo = fileManager.requestInfo[self.header['id']]
        self.fileInfo.fileType = self.header['filetype']
        self.fileInfo.size = self.header['length']
        self.file = open(self.fileInfo.filename, 'w')
        self.reciveData = True

    def handle_close(self):
        debug("PFC:Close")
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
    PushFileServer(9999, reuseAddress=True) # Nie jestem pewien, czy w końcowym kodzie powinno być reuseAddress, ale do debugowania się nada
    asyncore.loop()
