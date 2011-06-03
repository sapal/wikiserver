#!/usr/bin/env python
# coding=utf-8
import os

databaseFile = "base.db"
httpPort = 8080
httpsPort = 8081
cacheDir = 'cache'
cacheMaxSize = 100*1024**2 # 100 MB
_f = os.path.abspath(__file__)
dataDir = _f[:_f.rfind(os.sep)-4] + 'data'

# dostarczane z klientem
SSL_C_CACERTS = 'ca_certs'

# dostarczane z serwerem
SSL_S_CERTFILE = 'server.crt'
SSL_S_KEYFILE = 'server.key'

