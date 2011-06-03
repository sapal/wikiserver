# coding=utf-8

import asynchat, asyncore
import socket
import ssl
import errno
import select

from config import SSL_C_CACERTS, SSL_S_CERTFILE, SSL_S_KEYFILE

def _log(msg):
    print "[SSLSupport::] ", msg

class SSLAsyncChat(asynchat.async_chat):
    """ Asynchroniczna komunikacja ze wsparciem SSL """
    def connect(self, host):
        """ Mapuje metody send i recv na uwzgledniajace SSL. """
        _log("Remapping recv & send")
        self.send = self._mysend
        self.recv = self._myrecv
        asynchat.async_chat.connect(self, host)

    """ Inicjalizuje wsparcie SSL po stronie serwera. """
    def init_server_side(self):
        _log("server socket wrapping")
        self.ssl = ssl.wrap_socket(self.socket, server_side=True, certfile=SSL_S_CERTFILE, keyfile=SSL_S_KEYFILE, do_handshake_on_connect=False)
        while True:
            try:
                self.ssl.do_handshake()
                break
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.ssl], [], [])
                elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.ssl], [])
                else:
                    raise
        self.set_socket(self.ssl)
        self.send = self._mysend
        self.recv = self._myrecv
        
    def handle_connect(self):
        """ Obkłada socket klienta protokołem SSL. """
        _log("Switching transmission to SSL (ClientSide)")
        self.ssl = ssl.wrap_socket(self.socket, cert_reqs=ssl.CERT_REQUIRED, do_handshake_on_connect=False, ca_certs=SSL_C_CACERTS)
        self.set_socket(self.ssl)
        while True:
            try:
                self.ssl.do_handshake()
                break
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.ssl], [], [])
                elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.ssl], [])
                else:
                    raise

    def _mysend(self, data):
        """ Odpowiednik send() dla połączeń SSL """
        _log("SSL send")
        try:
            result = self.write(data)
            return result
        except ssl.SSLError, why:
            _log(why)
            _log(why.args)
            if why[0] in (asyncore.EWOULDBLOCK, errno.ESRCH):
                return 0
            else:
                raise ssl.SSLError, why
            return 0
 
    def _myrecv(self, buffer_size):
        """ Odpowiednik recv() dla połączeń SSL """
        _log("SSL recv")
        try:
            data = self.read(buffer_size)
            if not data:
                self.handle_close()
                return ''
            return data
        except ssl.SSLError, why:
            _log(why)
            _log(why.args)
            if why[0] in (asyncore.ECONNRESET, asyncore.ENOTCONN, 
                          asyncore.ESHUTDOWN):
                self.handle_close()
                return ''
            elif why[0] == errno.ENOENT:
                # Required in order to keep it non-blocking
                return ''
            else:
                raise
                

 
class SSLAsyncDispatcher(asyncore.dispatcher):
    """ Asynchroniczny dispatcher ze wsparciem SSL. """

