# coding=utf-8

import threading
import random
import os

class FileInfo :
    '''Klasa odpowiedzialna za dostarczanie informacji o plikach'''
    def __init__(self) :
        self.modifyTime = 0 
        self.size = 0 
        self.currentSize = 0
        self.filename = ""
        self.fileModified = threading.Condition
        self.fileType = "not found"

    def sizeChanged (self, newSize) :
        """ Zmienia currentSize i robi fileModified.notifyAll() """
        self.fileModified.acquire()
        self.fileModified.notifyAll()
        pass

class FileManager :
    '''Klasa zapewniająca dostęp do plików (singleton)'''
    def __init__(self) :
        self.hiddenServerConnections = {} # słownik: nazwa użytkownika (string) -> HiddenServerConnection
        self.requestInfo = {} # słownik: idZapytania(int) -> FileInfo
        self.fileInfo = {} # słownik: ścieżka do pliku (sring) -> FileInfo o najpóźniejszym czasie modyfikacji
        pass

    def getFileInfo (self, path) :
        """ zwraca FileInfo odpowiedniego plkiu """
        info = FileInfo()
        if path.strip() == "/":
            f = open("users.ls","w")
            for user in self.hiddenServerConnections.keys():
                f.write(user+"\n")
            f.close()
            info.filename = "users.ls"
            info.fileType = "directory"
        #TODO: Zwrócić coś sensownego
        elif random.choice([True, False]):
            info.filename = "test.html"
            info.fileType = "file"
        else:
            info.filename = "testdir.ls"
            info.fileType = "directory"
        info.size = info.currentSize = os.path.getsize(info.filename)
        return info

    def processResponse (self, requestId, HSresponse) :
        """ Przetwarza odpowiedź od HiddenServera i uaktualnia odpowiednie struktury """
        # returns 
        pass

fileManager = FileManager()
