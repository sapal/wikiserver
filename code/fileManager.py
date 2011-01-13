# coding=utf-8

import threading
import os
import time
import config
from logging import basicConfig, debug, DEBUG
basicConfig(filename='log', level=DEBUG, filemode='w')
#def debug(x):
#    print(x)

class FileInfo :
    '''Klasa odpowiedzialna za dostarczanie informacji o plikach'''
    def __init__(self) :
        self.modifyTime = 0.0
        self.size = -1 # to oznacza, że PushFileConnection jeszcze się nie podłączyło
        self.currentSize = 0
        self.path = "" # bezwzględna ścieżka do pliku
        self.filename = ""
        self.fileModified = threading.Condition()
        self.fileType = "not found"
        self.usingLock = threading.RLock() # żeby zdobyć ten lock trzeba już mieć fileManager.requestInfoLock
        self.usersCount = 0 # liczba procesów używających danego pliku 
        self.lastUse = 0
        self.useCount = 0
        self.broken = False

    def setBroken(self):
        """Zaznacza plik jako zepsuty i usuwa go z fileManager.fileInfo,
        jeśli to konieczne."""
        global fileManager
        with fileManager.requestInfoLock:
            with self.fileModified:
                self.broken = True
                self.fileModified.notifyAll()
                try:
                    if fileManager.fileInfo[self.path] is self:
                        del fileManager.fileInfo[self.path]
                except KeyError:
                    pass

    def setModifyTime(self, newTime):
        """Zmienia czas modyfikacji FileInfo uaktualniając
        fileManager.fileInfo."""
        global fileManager
        self.modifyTime = newTime
        with fileManager.requestInfoLock:
            if (self.path not in fileManager.fileInfo 
                    or self.modifyTime > fileManager.fileInfo[self.path].modifyTime):
                #print("UPDATE fileInfo({0})".format(self.modifyTime))
                fileManager.fileInfo[self.path] = self

    def sizeChanged(self, newSize):
        """ Zmienia currentSize i robi fileModified.notifyAll() """
        with self.fileModified:
            self.currentSize = newSize
            self.fileModified.notifyAll()

    def startUsing(self):
        """Zaczynam pracę z tym FileInfo,
        proszę go nie usuwać."""
        global fileManager
        #print("startUsing" + str(self))
        with fileManager.requestInfoLock:
            with self.usingLock:
                self.usersCount += 1
                self.lastUse = time.time()
                self.useCount += 1

    def stopUsing(self):
        """Skończyłem pracę z tym FileInfo,
        już mi nie jest potrzebne."""
        global fileManager
        #print("stopUsing" + str(self))
        with fileManager.requestInfoLock:
            with self.usingLock:
                self.usersCount -= 1

class FileManager :
    '''Klasa zapewniająca dostęp do plików (singleton)'''
    def __init__(self) :
        self.hiddenServerConnections = {} # słownik: nazwa użytkownika (string) -> HiddenServerConnection
        self.requestInfo = {} # słownik: idZapytania(int) -> FileInfo
        self.fileInfo = {} # słownik: ścieżka do pliku (string) -> FileInfo o najpóźniejszym czasie modyfikacji
        self.lastRequestId = 0
        self.requestInfoLock = threading.RLock() # lock blokujący dostęp do requestInfo i fileInfo
        self.idLock = threading.RLock()

    def removeCache(self):
        """Usuwa wszystkie pliki z cache (także te używane)."""
        with self.requestInfoLock:
            toRemove = [(id,f) for (id,f) in self.requestInfo.items()]
            for id, f in toRemove:
                try:
                    del self.requestInfo[id]
                    os.remove(f.filename)
                except (IOError,OSError):
                    debug("błąd przy usuwaniu pliku "+f.filename)
    
    def cleanCache(self):
        """Usuwa niepotrzebne pliki z cache."""
        with self.requestInfoLock:
            fileInfos = set((id,f) for (id,f) in self.requestInfo.items())
            totalSize = sum(f.size for (id,f) in fileInfos)
            cacheMax = config.cacheMaxSize
            if totalSize > cacheMax:
                toRemove = sorted([(id,f) for (id,f) in fileInfos if f.usersCount == 0], 
                        key=lambda (id,f):(f.modifyTime - f.lastUse - f.useCount*120))
                for id,f in toRemove:
                    try:
                        del self.requestInfo[id]
                        if f.path in self.fileInfo:
                            del self.fileInfo[f.path]
                        os.remove(f.filename)
                        totalSize -= f.size
                        if totalSize <= cacheMax:
                            break
                    except BaseException as e:
                        print("ERROR(CACHE):"+str(e))

    def startUsingFileInfo(self, filename):
        """Zwraca fileInfo pliku filename (ścieżka bezwzględna)
        o najpóźniejszym czasie modyfikacji i zaczyna go używać.
        Gdy taki nie istnieje, zwraca nowe FileInfo."""
        if len(filename) == 0 or filename[0] != '/':
            filename = '/'+filename
        with self.requestInfoLock:
            if filename in self.fileInfo:
                info = self.fileInfo[filename]
            else:
                info = FileInfo()
            info.startUsing()
            return info

    def nextRequestId(self):
        """Zwraca następne id dla zapytania."""
        with self.idLock:
            self.lastRequestId += 1
            return self.lastRequestId

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
            return config.cacheDir + '/users' #users to specjalny plik, w którym wylistowani są aktywni użytkownicy
        if user is None:
        	user = self.getUser(path)
        	path = self.getRelativePath(path)
        path = path.replace('/','.')
        if id is None:
            id = self.fileInfo['{user}.{path}'.format(user=user, path=path)]
        return config.cacheDir + "/{id}.{user}.{path}".format(id=id, user=user, path=path)

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
        if filename == config.cacheDir + "/users":
            debug('************************************* ASK FOR USERS') # dorota
            f = open(filename,"w")
            for user in self.hiddenServerConnections.keys():
                debug('there is' + user)                                 # dorota
                f.write(user+"\n")
            f.close()
            info.filename = filename
            info.fileType = "directory"
            info.size = info.currentSize = os.path.getsize(info.filename)
            info.modifyTime = time.time()
            with self.requestInfoLock:
                self.requestInfo[id] = info
            debug('********************************************* END')   # dorota
        else:
            try:
                with self.requestInfoLock:
                    self.requestInfo[id] = FileInfo()
                    self.requestInfo[id].path = path
                    self.requestInfo[id].filename = filename
                debug("getFileInfo({0}), sending request".format(filename))
                cond = threading.Condition()
                with cond:
                    user = self.getUser(path)
                    self.hiddenServerConnections[user].requestQueue.put({
                        'filename':self.getRelativePath(path),
                        'id':id,
                        'originalRequest':originalRequest,
                        'answerCondition':cond})
                    debug("getFileInfo({0}) waiting".format(filename))
                    cond.wait()
                debug("getFileInfo({0}), request completed".format(filename))
                with self.requestInfoLock:
                    info = self.requestInfo[id]
                #Wait for PushFileConnection to establish:
                with info.fileModified:
                    if info.size == -1:
                        info.fileModified.wait()
            except BaseException:
                import traceback
                debug(traceback.format_exc())
                return FileInfo()
        debug("getFileInfo({0}):{1}".format(path,str(info)))
        debug(self.fileInfo)
        return info

    def processResponse (self, requestId, HSresponse, fileInfo) :
        """ Przetwarza odpowiedź od HiddenServera i uaktualnia odpowiednie struktury """
        with self.requestInfoLock:
            if HSresponse['response'] == 'OK':
                self.requestInfo[requestId] = fileInfo
            elif HSresponse['response'] == 'OLD':
                self.requestInfo[requestId].setModifyTime(float(HSresponse['modifytime']))
            elif HSresponse['response'] == 'NOPE':
                self.requestInfo[requestId].filetype = 'not found'
                self.requestInfo[requestId].size = 0
                self.requestInfo[requestId].currentSize = 0
            self.requestInfo[requestId].startUsing()
            self.cleanCache()

fileManager = FileManager()
