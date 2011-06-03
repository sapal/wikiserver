#!/usr/bin/env python
# coding=utf-8
import sqlite3
import config
import hashlib
from helper import toUnicode

class PasswordDatabase(object):
    """Klasa odpowiedzialna za trzymanie haseł.
    Przy tworzeniu tego obiektu 
    używana jest baza danych z pliku config.databaseFile ."""
    def __init__(self):
        self.database = sqlite3.connect(config.databaseFile)
        try:
            self.database.execute("SELECT * FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("Database doesn't exists: creating")
            self.database.execute("""CREATE TABLE users (
                name text,
                password text)""")
            self.database.commit()

    def hashPassword(self, password):
        """Hashuje hasło do celów przechowywania w bazie."""
        s = hashlib.sha512()
        s.update(password)
        return unicode(s.hexdigest(), "utf-8")

    def addUser(self, name, password):
        """Dodaje nowego użytkownika do bazy danych. Hasło jest 
        przechowywane jako suma sha512."""

        self.database.execute("""INSERT INTO users (name, password)
            VALUES (?, ?)""", (toUnicode(name), self.hashPassword(password)))
        self.database.commit()

    def removeUser(self, name):
        """Usuwa użytkownika z bazy danych."""
        self.database.execute("""DELETE FROM users
            WHERE name = ?""", (toUnicode(name), ))
        self.database.commit()

    def authenticateUser(self, name, password):
        """Autentykuje danego użytkownika (sprawdza, czy name
        i password zgadzają się z tymi w bazie)."""
        cur = self.database.cursor()
        cur.execute("""SELECT * FROM users WHERE 
            name = ? AND password = ?""", (toUnicode(name), self.hashPassword(password)))
        if cur.fetchone():
            return True
        else:
            return False

    def getUsers(self):
        """Zwraca listę wszystkich zarejestrowanych użytkowników."""
        cur = self.database.cursor()
        cur.execute("""SELECT name FROM users""")
        return [ r[0] for r in cur.fetchall() ]


