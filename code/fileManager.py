# coding=utf-8

import threading
import os

class FileInfo :
    '''Klasa odpowiedzialna za dostarczanie informacji o plikach'''
    def __init__(self) :
        self.modifyTime = 0 
        self.size = -1 # to oznacza, że PushFileConnection jeszcze się nie podłączyło
        self.currentSize = 0
        self.path = "" # bezwzględna ścieżka do pliku
        self.filename = ""
        self.fileModified = threading.Condition()
        self.fileType = "not found"

    def setModifyTime(self, newTime):
        """Zmienia czas modyfikacji FileInfo uaktualniając
        fileManager.fileInfo."""
        global fileManager
        self.modifyTime = newTime
        #with fileManager.fileInfoLock:
        fileManager.fileInfoLock.acquire()
        if (self.path not in fileManager.fileInfo 
                or self.modifyTime > fileManager.fileInfo[path].modifyTime):
            fileManager.fileInfo[path] = self
        fileManager.fileInfoLock.release()

    def sizeChanged (self, newSize) :
        """ Zmienia currentSize i robi fileModified.notifyAll() """
        self.fileModified.acquire()
        self.currentSize = newSize
        self.fileModified.notifyAll()
        self.fileModified.release()

class FileManager :
    '''Klasa zapewniająca dostęp do plików (singleton)'''
    def __init__(self) :
        self.hiddenServerConnections = {} # słownik: nazwa użytkownika (string) -> HiddenServerConnection
        self.requestInfo = {} # słownik: idZapytania(int) -> FileInfo
        self.fileInfo = {} # słownik: ścieżka do pliku (string) -> FileInfo o najpóźniejszym czasie modyfikacji
        self.lastRequestId = 0
        self.fileInfoLock = threading.Lock()
        self.idLock = threading.Lock()

    def nextRequestId(self):
        """Zwraca następne id dla zapytania."""
        self.idLock.acquire()
        self.lastRequestId += 1
        id = self.lastRequestId
        self.idLock.release()
        return id
    
    def removeId(self, filename):
        """Usuwa id z ścieżki do pliku
        (żeby można było użyć jej jako klucza w self.fileInfo."""
        if filename == 'cache/users':
            return 'users'
        dot = filename.find('.')
        return filename[dot+1:]

    def _stripPath(self, path):
        """Usuwa zbędne spacje/slashe ze ścieżki."""
        path = path.strip()
        if path[0] == '/':
            path = path[1:]
        if len(path) > 0 and path[-1] == '/':
            path = path[:-1]
        return path

    def getRelativePath(self, path):
        """Zwraca względną (odpowiednią do przekazania HiddenServerowi)
        nazwę pliku."""
        path = self._stripPath(path)
        slash = path.find('/')
        return (path[slash:] if slash != -1 else "/")

    def getFilename(self, path, user=None, id=None):
        """Zwraca nazwę pliku (na dysku Servera) 
        o ścieżce path. Jeżeli user jest ustawione, to 
        ścieżka jest względna (czyli prawdziwa ścieżka to /user[/]path).
        Jeśli id jest ustawione, zwracana jest nazwa pliku dla konkretnego
        zapytania, wpp nazwa najpóźniej zmodyfikowanej wersji tego pliku.
        """
        path = self._stripPath(path)
        if path == '':
            return 'cache/users' #users to specjalny plik, w którym wylistowani są aktywni użytkownicy
        if user is None:
        	user = self.getUser(path)
        	path = self.getRelativePath(path)
        path = path.replace('/','.')
        if id is None:
            id = self.fileInfo['{user}.{path}'.format(user=user, path=path)]
        return "cache/{id}.{user}.{path}".format(id=id, user=user, path=path)

    def getUser(self, path):
        """Zwraca nazwę użytkownika na podstawie ścieżki (bezwzględnej)."""
        path = self._stripPath(path)
        slash = path.find('/')
        return (path[:slash] if slash != -1 else path)


    def getFileInfo (self, path, originalRequest):
        """ zwraca FileInfo odpowiedniego plkiu """
        info = FileInfo()
        id = self.nextRequestId()
        filename = self.getFilename(path, id=id)
        if filename == "cache/users":
            print '************************************* ASK FOR USERS' # dorota
            f = open(filename,"w")
            for user in self.hiddenServerConnections.keys():
                print 'there is' + user                                 # dorota
                f.write(user+"\n")
            f.close()
            info.filename = filename
            info.fileType = "directory"
            info.size = info.currentSize = os.path.getsize(info.filename)
            print '********************************************* END'   # dorota
        else:
            try:
                self.requestInfo[id] = FileInfo()
                self.requestInfo[id].path = path
                self.requestInfo[id].filename = filename
                print("getFileInfo({0}), sending request".format(filename))
                cond = threading.Condition()
                cond.acquire()
                user = self.getUser(path)
                self.hiddenServerConnections[user].requestQueue.put({
                    'filename':self.getRelativePath(path),
                    'id':id,
                    'originalRequest':originalRequest,
                    'answerCondition':cond})
                cond.wait()
                cond.release()
                print("getFileInfo({0}), request completed".format(filename))
                info = self.requestInfo[id]
                #Wait for PushFileConnection to establish:
                info.fileModified.acquire()
                if info.size == -1:
                    info.fileModified.wait()
                info.fileModified.release()
            except BaseException as e:
                import traceback
                traceback.print_exc()
                return FileInfo()
        print("getFileInfo({0}):{1}".format(path,str(info)))
        print(self.fileInfo)
        return info

    def processResponse (self, requestId, HSresponse, fileInfo) :
        """ Przetwarza odpowiedź od HiddenServera i uaktualnia odpowiednie struktury """
        if HSresponse['response'] == 'OK':
            self.requestInfo[requestId] = fileInfo
        elif HSresponse['response'] == 'OLD':
            self.requestInfo[requestId].setModifyTime(int(HSresponse['modifytime']))

fileManager = FileManager()
