Helper
======

Ten moduł (helper.py) zawiera funkcje potrzebne do parsowania i formatowania danych zgodnie z protokołami SW i PF.

.. automodule:: helper
	:members:

Przykładowo::

    >>> txt = "MYNAMEIS\nusername:name\n\n"
    >>> parseData(txt)
    {'response': 'MYNAMEIS', 'username': 'name'}

    >>> helper.formatDate(1295360000)
    'Tue, 18 Jan 2011 14:13:20 GMT'
    
.. 
