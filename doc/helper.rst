Helper
======

Ten moduł (helper.py) zawiera funkcje potrzebne do parsowania i formatowania danych zgodnie z protokołami SW i PF.

.. automodule:: helper
	:members:

Przykładowo::

    >>> txt = "MYNAMEIS\nusername:name\n\n"
    >>> parseData(txt)
    {'response': 'MYNAMEIS', 'username': 'name'}

.. 
