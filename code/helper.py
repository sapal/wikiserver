# coding=utf-8
from wsgiref.handlers import format_date_time

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

