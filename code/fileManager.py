# coding=utf-8

import threading
import os
import shutil
import time
import config
from helper import getAuthentication
from database import PasswordDatabase
from logging import basicConfig, debug, DEBUG
basicConfig(filename='log', level=DEBUG, filemode='w')

class FileInfo :
    '''Klasa odpowiedzialna za dostarczanie informacji o plikach.
    
    Pola:
    modifyTime = 0 -- Data ostatniej modyfikacji pliku (na HiddenServerze)
    size = -1 -- Wielkość pliku (w bajtach). Wartość -1 oznacza, że PushFileConnection jeszcze się nie rozpoczęło i wielkość jest nieznana
    currentSize = 0 -- Aktualna wielkość pliku (ile się ściągnęło na Server)
    path = "" -- Bezwzględna ścieżka do pliku (użytkownik/katalog/.../plik)
    filename = "" -- Nazwa pliku na Serverze
    fileModified = threading.Condition() -- Condition, na którym robione jest notifyAll, gdy plik "filename" jest modyfikowany
    fileType = "not found" -- Typ pliku. Możliwe są cztery wartości: "not found"/"authentication required"/"file"/"directory"
    usersCount = 0 -- Liczba wątków używających tego pliku (wątki używające pliku są zobowiązane wywołać metody startUsing oraz stopUsing)
    lastUse = 0 -- Czas ostatniego użycia tego pliku (ustawiane w startUsing)
    useCount = 0 -- Liczba użyć tego pliku (ustawiane w startUsing)
    broken = False -- Czy plik jest popsuty (np. połączenie zostało przerwane podczas jego przesyłania)
    '''
    def __init__(self) :
        """Tworzy FileInfo z domyślnymi wartościami pól."""
        self.modifyTime = 0.0 
        self.size = -1 
        self.currentSize = 0
        self.path = "" 
        self.filename = ""
        self.fileModified = threading.Condition()
        self.fileType = "not found"
        self.usingLock = threading.RLock() # żeby zdobyć ten lock trzeba już mieć fileManager.requestInfoLock
        self.usersCount = 0 
        self.lastUse = 0
        self.useCount = 0
        self.broken = False

    def __str__(self):
        return "FileInfo<path:'{0}' fileType:'{1}'>".format(self.path, self.fileType)

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
        with fileManager.requestInfoLock:
            with self.usingLock:
                self.usersCount += 1
                self.lastUse = time.time()
                self.useCount += 1

    def stopUsing(self):
        """Skończyłem pracę z tym FileInfo,
        już mi nie jest potrzebne."""
        global fileManager
        with fileManager.requestInfoLock:
            with self.usingLock:
                self.usersCount -= 1

class FileManager :
    '''Klasa zapewniająca dostęp do plików (singleton)
    
    Pola:
    hiddenServerConnections = {} -- Słownik: nazwa użytkownika (string) -> HiddenServerConnection przechowujący informacje o połączeniach z HiddenServerami
    requestInfo = {} Słownik: idZapytania(int) -> FileInfo
    fileInfo = {} Słownik: ścieżka do pliku (string) -> FileInfo o najpóźniejszym czasie modyfikacji
    '''
    def __init__(self) :
        """Tworzy nowy FileManager. Nie powinno się tworzyć więcej niż jednego FileManagera"""
        self.hiddenServerConnections = {} 
        self.requestInfo = {} 
        self.fileInfo = {} 
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
            totalSize = sum(f.size for f in set(f for (id,f) in fileInfos))
            cacheMax = config.cacheMaxSize
            if totalSize > cacheMax:
                toRemove = sorted([(id,f) for (id,f) in fileInfos if f.usersCount == 0], 
                        key=lambda (id,f):(f.modifyTime - f.lastUse - f.useCount*120))
                for id,f in toRemove:
                    try:
                        del self.requestInfo[id]
                        if f.path in self.fileInfo:
                            del self.fileInfo[f.path]
                        if f.fileType not in ('not found', 'authentication required'):
                            os.remove(f.filename)
                        totalSize -= f.size
                        if totalSize <= cacheMax:
                            break
                    except BaseException:
                        pass

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
        if len(path) > 0 and path[0] == '/':
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
        path = self._stripPath(path)
        info.path = path
        info.filename = filename
        if filename == config.cacheDir + "/users":
            f = open(filename,"w")
            if PasswordDatabase().authenticateUser(*getAuthentication(originalRequest)):
                for user in self.hiddenServerConnections.keys():
                    f.write(user+"\n")
                info.fileType = "directory"
            else:
                f.write("Brak uprawnień\n")
                info.fileType = "authentication required"
            f.close()
            debug(info.fileType)
            info.filename = filename
            info.size = info.currentSize = os.path.getsize(info.filename)
            info.setModifyTime(time.time())
            with self.requestInfoLock:
                self.requestInfo[id] = info
                info.startUsing()
        elif self.getUser(path) == 'favicon.ico':
            cachedFilename =  config.cacheDir + os.sep + 'favicon.ico'
            dataFilename = config.dataDir + os.sep + 'favicon.ico'
            mtime = os.path.getmtime(dataFilename)
            if not os.path.exists(cachedFilename): 
                shutil.copy(dataFilename, cachedFilename)
                os.utime(cachedFilename, (mtime, mtime))
            info.filename = config.cacheDir + os.sep + 'favicon.ico'
            info.fileType = "file"
            info.size = info.currentSize = os.path.getsize(info.filename)
            info.setModifyTime(mtime)
            with self.requestInfoLock:
                self.requestInfo[id] = info
                info.startUsing()
        else:
            try:
                with self.requestInfoLock:
                    self.requestInfo[id] = info
                debug("getFileInfo({0}), sending request {1}".format(filename, id))
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
                #Czekaj, aż zacznie się PushFileConnection:
                while info.size == -1:
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
            debug("PROCESS: {0}".format(HSresponse))
            if HSresponse['response'] == 'OK':
                self.requestInfo[requestId] = fileInfo
            elif HSresponse['response'] == 'OLD':
                self.requestInfo[requestId].setModifyTime(float(HSresponse['modifytime']))
            elif HSresponse['response'] == 'NOPE':
                self.requestInfo[requestId].fileType = 'not found'
                self.requestInfo[requestId].size = 0
                self.requestInfo[requestId].currentSize = 0
            elif HSresponse['response'] == 'REJ':
                print("REJ")
                self.requestInfo[requestId].fileType = "authentication required"
                self.requestInfo[requestId].size = 0
                self.requestInfo[requestId].currentSize = 0
            debug(str(requestId) + u" " +str(self.requestInfo[requestId]))
            self.requestInfo[requestId].startUsing()
            self.cleanCache()

fileManager = FileManager()
