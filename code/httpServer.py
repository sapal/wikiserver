# coding=utf-8
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from fileManager import fileManager,FileInfo
from urllib import quote,unquote
from SocketServer import ThreadingMixIn
from mimetypes import guess_type
from logging import basicConfig, debug, DEBUG
#basicConfig(filename='httpServer.log', level=DEBUG, filemode='w')

class HttpRequest(BaseHTTPRequestHandler):
    '''Klasa odpowiedzialna za obsługę HTTP'''
    def handle_error(self):
        print("HTTP:ERROR")
    def do_GET(self):
        """Obsługa GET"""
        info = FileInfo()
        try:
            info = fileManager.getFileInfo(unquote(self.path), 
                    ' '.join([self.command,
                        self.path,
                        self.request_version,
                        str(self.headers)]))
            debug("HTTP:info:{0}".format(info))
            if info.fileType == "not found":
                raise IOError()
            self.send_response(200)
            type = guess_type(info.filename)[0]
            if type is None:
                type = 'text/html'
            self.send_header('Content-type', type) #TODO
            self.end_headers()
            f = open(info.filename)
            if info.fileType == "file":
                written = 0
                chunkSize = 1024
                while written < info.size:
                    if written == info.currentSize:
                        with info.fileModified:
                            info.fileModified.wait()
                    chunk = f.read(min(chunkSize, info.currentSize-written))
                    written += len(chunk)
                    self.wfile.write(chunk)
                    #debug("HTTP: "+str(written))
                    #debug(chunk)
            elif info.fileType == "directory":
                if self.path[-1] == '/':
                    self.path = self.path[:-1]
                while info.currentSize < info.size:
                    with info.fileModified:
                        info.fileModified.wait()
                self.wfile.write('<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8"/></head><body><ul>\n')
                for line in f:
                    self.wfile.write('<li><a href="{0}/{2}">{1}</a></li>\n'.format(self.path, line.strip(), quote(line.strip())))
                self.wfile.write("</body></html>\n")
        except IOError:
            self.send_error(404,'Nie znaleziono pliku {0}'.format(self.path))
        finally:
            self.wfile.flush()
            info.stopUsing()

class HttpServer(ThreadingMixIn, HTTPServer):
    '''Klasa odpowiedzialna za tworzenie HttpRequestów'''
    def __init__(self, interface='', port=8080, handler=HttpRequest) :
        HTTPServer.__init__(self,(interface,port),handler)

def start():
    server = HttpServer()
    print("Starting HttpServer.")
    server.serve_forever()
