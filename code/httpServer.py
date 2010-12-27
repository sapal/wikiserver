# coding=utf-8
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from fileManager import fileManager
from urllib import quote,unquote

class HttpRequest(BaseHTTPRequestHandler):
    '''Klasa odpowiedzialna za obsługę HTTP'''
    def do_GET(self):
        try:
            info = fileManager.getFileInfo(unquote(self.path), 
                    ' '.join([self.command,
                        self.path,
                        self.request_version,
                        str(self.headers)]))
            print("HTTP:info:{0}".format(info))
            if info.fileType == "not found":
                raise IOError()
            self.send_response(200)
            self.send_header('Content-type', 'text/html') #TODO
            self.end_headers()
            f = open(info.filename)
            if info.fileType == "file":
                written = 0
                chunkSize = 10
                while written < info.size:
                    if written == info.currentSize:
                        info.fileModified.acquire()
                        info.fileModified.wait()
                        info.fileModified.release()
                    chunk = f.read(min(chunkSize, info.currentSize-written))
                    written += len(chunk)
                    self.wfile.write(chunk)
                    print(chunk)
            elif info.fileType == "directory":
                if self.path[-1] == '/':
                    self.path = self.path[:-1]
                while info.currentSize < info.size:
                    info.fileModified.acquire()
                    info.fileModified.wait()
                    info.fileModified.release()
                self.wfile.write("<html><head></head><body><ul>\n")
                for line in f:
                    self.wfile.write('<li><a href="{0}/{2}">{1}</a></li>\n'.format(self.path, line.strip(), quote(line.strip())))
                self.wfile.write("</body></html>\n")
        except IOError:
            self.send_error(404,'Nie znaleziono pliku {0}'.format(self.path))

class HttpServer(HTTPServer):
    '''Klasa odpowiedzialna za tworzenie HttpRequestów'''
    def __init__(self, interface='', port=8080, handler=HttpRequest) :
        HTTPServer.__init__(self,(interface,port),handler)

def start():
    server = HttpServer()
    print("Starting HttpServer.")
    server.serve_forever()