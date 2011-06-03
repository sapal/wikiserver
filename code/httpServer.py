# coding=utf-8
import socket, ssl

from SocketServer import BaseServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from fileManager import fileManager,FileInfo
from urllib import quote,unquote
from SocketServer import ThreadingMixIn
from mimetypes import guess_type
from logging import debug
from helper import formatDate

import config

class HttpRequest(BaseHTTPRequestHandler, object):
    '''Klasa odpowiedzialna za obsługę HTTP'''
    def handle_error(self):
        """Nadpisuje odpowiednią metodę w BaseHTTPRequestHandler."""
        print("HTTP:ERROR")

    def do_POST(self):
        """Nadpisuje odpowiednią metodę w BaseHTTPRequestHandler."""
        self.answerGET()
    def do_GET(self):
        """Nadpisuje odpowiednią metodę w BaseHTTPRequestHandler."""
        self.answerGET()
    def do_HEAD(self):
        """Nadpisuje odpowiednią metodę w BaseHTTPRequestHandler."""
        self.answerGET(headerOnly=True)
    def answerGET(self, headerOnly=False):
        """Wyślij odpowiedni nagłówek i plik.
        Jeśli opcja headerOnly jest ustawiona -- sam nagłówek"""
        info = FileInfo()
        try:
            info = fileManager.getFileInfo(unquote(self.path), 
                    ' '.join([self.command,
                        self.path,
                        self.request_version,
                        str(self.headers)]))
            if info.fileType == "not found":
                raise IOError()
            elif info.fileType == "authentication required":
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm=\"Wikiserver\"')
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                return
            if 'If-Modified-Since' in self.headers: 
                if self.headers['If-Modified-Since'] == formatDate(info.modifyTime):
                    self.send_response(304)
                    return
            begin = 0
            end = info.size
            partial = False
            try:
                if "range" in self.headers:
                    begin,end = map(int,self.headers["range"].partition('=')[2].split('-'))
                    partial = True
            except:
                pass
            if partial:
                self.send_response(206)
            else:
                self.send_response(200)
            type = guess_type(info.filename)[0]
            if type is None or info.fileType == "directory":
                type = 'text/html; charset=utf-8'
            self.send_header('Content-type', type)
            self.send_header('Last-Modified', formatDate(info.modifyTime))
            length = end - begin
            size = info.size
            if info.fileType == "directory":
                listing = self.getDirectoryListing(self.path, info)
                size = len(listing)
                if not partial:
                    begin = 0
                    end = size
                    length = end-begin
            if partial:
                self.send_header('Content-Range:', 'bytes {0}-{1}/{2}'.format(begin, end, size))
            self.send_header('Content-Length', length)
            self.send_header('Connection', 'close')
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            if headerOnly:
                return
            if info.fileType == "file":
                f = open(info.filename, 'r')
                written = 0
                chunkSize = 16*1024
                while written < info.size:
                    if info.broken:
                        raise IOError("błąd przy pobieraniu pliku")
                    if written == info.currentSize:
                        with info.fileModified:
                            info.fileModified.wait()
                    chunk = f.read(min(chunkSize, info.currentSize-written))
                    pbegin = max(0, min(begin-written, len(chunk)))
                    pend = min(len(chunk), max(end-written, 0))
                    part = chunk[pbegin:pend]
                    written += len(chunk)
                    if len(part) > 0:
                        self.wfile.write(part)
                    if written > end:
                        break
            elif info.fileType == "directory":
                self.wfile.write(listing)
        except IOError :
            debug(" ".join(["Błąd:",self.command, self.path, self.request_version, str(self.headers)]))
            import traceback
            debug(traceback.format_exc())
            try:
                self.send_error(404,'Nie znaleziono pliku {0}'.format(self.path))
            except BaseException :
                debug("Nie udało się wysłać odpowiedzi")
            debug("[/Błąd]")
        except BaseException :
            import traceback
            debug(traceback.format_exc())
        finally:
            info.stopUsing()

    def getDirectoryListing(self, path, fileInfo):
        """Zwraca listing katalogu opisanego za pomocą fileInfo.
        path to ścieżka (bezwzględna) do tego katalogu."""
        f = open(fileInfo.filename, 'r')
        res = []
        if path[-1] == '/':
            path = path[:-1]
        while fileInfo.currentSize < fileInfo.size:
            if fileInfo.broken:
                raise IOError("błąd przy pobieraniu pliku")
            with fileInfo.fileModified:
                fileInfo.fileModified.wait()
        res.append('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml"><head><meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>[wikiserver]:{0}</title>
        <link rel="shortcut icon" href="/favicon.ico" />
        </head><body><h1>[wikiserver]:{0}</h1>'''.format(unquote(path)))
        if path != '':
            res.append('<h3><a href="{0}/..">do góry</a></h3>\n'.format(path))
        res.append('<h2>{0}:</h2><ul>\n'.format(("Pliki" if path != '' else "Użytkownicy")))

        for line in sorted(f):
            res.append('<li><a href="{0}/{2}">{1}</a></li>\n'.format(path, line.strip(), quote(line.strip())))
        res.append("</ul></body></html>\n")
        return "".join(res)

    def log_message(self, format, *args):
        """Nadpisuje odpowiednią metodę w BaseHTTPRequestHandler."""
        print("HTTP: "+ (format%args)+ " {0}:{1}".format(*(self.client_address)))

class HttpServer(ThreadingMixIn, HTTPServer):
    '''Klasa odpowiedzialna za tworzenie HttpRequestów'''
    def __init__(self, interface='', port=config.httpPort, handler=HttpRequest, useSSL=True) :
        """Tworzy HttpServer na interfejsie interface ('' oznacza wszystkie interfejsy),
        porcie port z HTTPRequestHandlerem handler."""
        if not useSSL:
            HTTPServer.__init__(self,(interface,port),handler)
        else:
            BaseServer.__init__(self, (interface, port), handler)
            self.socket = ssl.wrap_socket( socket.socket(self.address_family, self.socket_type), server_side=True, certfile=config.SSL_S_CERTFILE, keyfile=config.SSL_S_KEYFILE)
            self.server_bind()
            self.server_activate()
        
def start(port, secure):
    """Uruchom HttpServer na porcie config.httpPort."""
    server = HttpServer(port=port, useSSL=secure)
    if not secure:
        print("Starting HttpServer")
    else:
        print("Starting HttpsServer")
    server.serve_forever()

