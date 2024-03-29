# coding=utf-8
from wsgiref.handlers import format_date_time
import base64
import re

def parseData(data):
    """ Funkcja zwracająca słownik, powstały w wyniku parsowania 
    argumentu funkcji, zgodnie z protokołem SW lub PF. """
    r = {}
    data = data.split('\n')
    r['response'] = data[0].strip().upper()
    for line in data[1:]:
        colon = line.find(':')
        if colon == -1:
            continue
        field = line[:colon].lower().strip()
        value = line[colon+1:]
        r[field] = value
    return r
   

def formatDate(timestamp):
    """Formatuje datę tak, jak każe HTTP (zwraca string)."""
    return format_date_time(timestamp)

def toUnicode(text):
    """Zamienia tekst na unicode (utf-8), o ile jeszcze nim nie jest."""
    if isinstance(text, unicode):
        return text
    else:
        return unicode(text, "utf-8")

def getAuthentication(httpRequest):
    """Zwraca informacje do autoryzacji (login, hasło)
    z requestu http (format INNY NIŻ w protokole SW 
    - nie zakodowane base64).
    W przypadku braku takowych zwraca ("","").
    PATRZ TEŻ: getAuthenticationBase64(base64httpRequest)
    
    UWAGA: Nie używać dwukropków w loginach (nie zadziała)."""
    request = httpRequest
    p = re.compile("^\s*Authorization\s*:\s*Basic\s*(\S*)", re.IGNORECASE|re.MULTILINE|re.UNICODE)
    m = p.search(request)
    try:
        return tuple(map(lambda x: unicode(x, "utf-8"), base64.b64decode(m.group(1)).split(":",1)))
    except:
        return (u"",u"")

def getAuthenticationBase64(base64httpRequest):
    """Zwraca informacje do autoryzacji (login, hasło)
    z zakodowanego base64 requestu http (format jak w protokole SW).
    W przypadku braku takowych zwraca ("","").
    
    UWAGA: Nie używać dwukropków w loginach (nie zadziała)."""
    request = base64.b64decode(base64httpRequest)
    return getAuthentication(request)

