# coding=utf-8

from fileManager import fileManager
import threading
import asynchat, asyncore
import socket
from Queue import Queue
from helper import parseData
import base64
from logging import debug
from ssl_asyncchat import SSLAsyncChat, SSLAsyncDispatcher

class HiddenServerConnection(SSLAsyncChat, object):
    '''Klasa reprezentująca trwałe połączenie HiddenServera z Serverem
    
    Pola:
    requestQueue = Queue() -- Kolejka zapytań do wysłania HiddenServerowi
    user = "" -- Nazwa użytkownika
    '''
    responses = ["OK", "OLD", "MYNAMEIS", "NOPE"]
    def __init__(self, sock, map=None):
        """Tworzy nowe HiddenServerConnection słuchające na gniazdku sock
        i dodane do mapy asyncore map (None oznacza domyślną mapę)."""
        self.buffer = ""
        asynchat.async_chat.__init__(self, sock, map=map)
        self.init_server_side()
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
                request['modifytime'] = info.modifyTime
                debug('REQUEST: '+self.user+' '+str(request))
                self.sentRequests.put((request, info))
            self.buffer += "GET\nfilename:{filename}\nmodifytime:{modifytime}\nid:{id}\noriginalRequest:{0}\n\n".format(
                base64.b64encode(request['originalRequest']), **request) 
            while len(self.buffer)>0:
                sent = self.send(self.buffer)
                self.buffer = self.buffer[sent:]
            debug("REQUEST SENT")

    def collect_incoming_data(self, data):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        self.data.append(data)

    def processResponse(self):
        """Funkcja przetwarzająca odpowiedź od HiddenServera."""
        global fileManager
        r = self.response
        self.response = {}
        if r['response'] == "MYNAMEIS":
            self.user = r['username'].strip()
            fileManager.hiddenServerConnections[self.user] = self
            print("SW: User '{0}' connected.".format(self.user))
            return
        else:
            with self.stopLock:
                request, info = self.sentRequests.get()
                fileManager.processResponse(request['id'], r, info)
                c = request['answerCondition']
                with c:
                    c.notify()
                info.stopUsing()

    def handle_error(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        debug("HSC:ERROR")

    def found_terminator(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        data = "".join(self.data)
        self.data = []
        self.response = parseData(data)
        self.processResponse()   

    def handle_close(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        with self.stopLock:
            debug("Close")
            self.close()
            while not self.sentRequests.empty():
                r,info = self.sentRequests.get(False)
                info.stopUsing()
            if self.user != "":
                del fileManager.hiddenServerConnections[self.user]

class HSServer(SSLAsyncDispatcher, object): # asyncore.dispatcher
    '''Klasa odpowiedzialna za tworzenie HiddenServerConnectionów'''

    def __init__(self, port, reuseAddress=False, map=None):
        """Tworzy nowy HSServer słuchający na porcie port
        i dodane do mapy asyncore map (None oznacza domyślną mapę).
        Opcja reuseAddres mówi, czy SO_REUSEADDR powinno być ustawione,
        czy nie."""
        asyncore.dispatcher.__init__(self, None, map)
        self.map = map
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuseAddress:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)

    def handle_accept(self):
        """Nadpisuje odpowiednią metodę w asyncore.dispatcher."""
        print "MIBDBG: cos do zaakceptowania"
        p = self.accept()
        print "zaakceptowano ", p
        if not p:
            return
        conn, addr = p
        print "tworze polaczenie"
        HiddenServerConnection(conn, self.map)
        
def startHSServer():
    """Uruchamia HSServer na domyślnym porcie (8888)."""
    m = {}
    HSServer(8888, reuseAddress=True, map=m) 
    print("Starting HSServer.")
    asyncore.loop(map=m)

class PushFileConnection(asynchat.async_chat, object):
    '''Klasa reprezentująca połączenie przesyłające plik z HiddenServera do Servera.
    Zapisuje dane do odpowiedniego pliku i przy każdym zapisie wywołuje sizeChanged().
    '''
    ac_in_buffer_size = 32*1024
    def __init__(self, sock, map=None):
        """Tworzy nowe PushFileConnection na gniazdku sock
        i dodane do mapy asyncore map (None oznacza domyślną mapę)."""
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
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        self.data.append(data)

    def handle_error(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        import traceback
        debug(traceback.format_exc())

    def formatHeader(self):
        """Sformatuj nagłówek (zamień stringi w self.header na odpowiednie
        typy."""
        try:
            for key in ('size','id'):
                self.header[key] = int(self.header[key])
            self.header['modifytime'] = float(self.header['modifytime'])
            self.header['type'] = self.header['type'].strip()
        except BaseException as e:
            print(e)
            print(str(self.header))

    @property
    def length(self):
        """Wielkość aktualnie ściąganego pliku."""
        return self.header['size']

    def found_terminator(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        global fileManager
        data = "".join(self.data)
        self.data = []
        if self.reciveData:
            self.recived += len(data)
            self.file.write(data)
            self.file.flush()
            self.fileInfo.sizeChanged(self.recived)
            if self.length == self.recived:
                debug("OK")
                return
            term = min(self.BUFFER_SIZE,self.length - self.recived)
            self.set_terminator(term)
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
        print("PUSH FILE: '{file}' (size:{size})".format(file=self.fileInfo.path, size=self.fileInfo.size))

    def handle_close(self):
        """Nadpisuje odpowiednią metodę w asynchat.async_chat."""
        debug("PFC:Close")
        if self.fileInfo.currentSize < self.fileInfo.size:
            self.fileInfo.setBroken()
        self.close()
        
class PushFileServer(asyncore.dispatcher, object):
    '''Klasa odpowiedzialna za tworzenie PushFileConnectionów'''

    def __init__(self, port, reuseAddress=True, map=None):
        """Tworzy nowy PushFileServer słuchający na porcie port
        i dodane do mapy asyncore map (None oznacza domyślną mapę).
        Opcja reuseAddres mówi, czy SO_REUSEADDR powinno być ustawione,
        czy nie."""
        asyncore.dispatcher.__init__(self, map=map)
        self.map = map
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuseAddress:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)

    def handle_accept(self):
        """Nadpisuje odpowiednią metodę w asyncore.dispatcher."""
        p = self.accept()
        if not p:
            return
        conn, addr = p
        PushFileConnection(conn, map=self.map)
        
def startPushFileServer():
    """Uruchamia PushFileServer na domyślnym porcie (9999)."""
    print("Starting PushFileServer")
    m = {}
    PushFileServer(9999, reuseAddress=True, map=m) 
    asyncore.loop(map=m)
