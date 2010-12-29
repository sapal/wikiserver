# coding=utf-8

import threading
import os

class FileInfo :
    '''Klasa odpowiedzialna za dostarczanie informacji o plikach'''
    def __init__(self) :
        self.modifyTime = 0 
        self.size = 0 
        self.currentSize = 0
        self.filename = ""
        self.fileModified = threading.Condition()
        self.fileType = "not found"

    def setModifyTime(self, newTime):
        global fileManager
        self.modifyTime = newTime
        #with fileManager.fileInfoLock:
        fileManager.fileInfoLock.acquire()
        if (self.filename not in fileManager.fileInfo 
                or self.modifyTime > fileManager.fileInfo[self.filename].modifyTime):
            fileManager.fileInfo[self.filename] = self
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
        self.idLock.acquire()
        self.lastRequestId += 1
        id = self.lastRequestId
        self.idLock.release()
        return id

    def getFileInfo (self, path, originalRequest) :
        """ zwraca FileInfo odpowiedniego plkiu """
        info = FileInfo()
        if path.strip() == "/":
            f = open("users","w")
            for user in self.hiddenServerConnections.keys():
                f.write(user+"\n")
            f.close()
            info.filename = "users"
            info.fileType = "directory"
            info.size = info.currentSize = os.path.getsize(info.filename)
        else:
            try:
                path = path[1:]
                if path[-1] == '/':
                    path = path[:-1]
                slash = path.find('/')
                user = path[:slash] if slash != -1 else path
                filename = path[slash+1:] if slash != -1 else ""
                id = self.nextRequestId()
                self.requestInfo[id] = FileInfo()
                self.requestInfo[id].filename = (user+"/"+filename).replace("/",'.')
                self.requestInfo[id].size = -1
                print("getFileInfo({0}/{1}), sending request".format(user,filename))
                cond = threading.Condition()
                cond.acquire()
                self.hiddenServerConnections[user].requestQueue.put({
                    'filename':filename,
                    'id':id,
                    'originalRequest':originalRequest,
                    'answerCondition':cond})
                cond.wait()
                cond.release()
                print("getFileInfo({0}/{1}), request completed".format(user,filename))
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
