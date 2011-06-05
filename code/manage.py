#!/usr/bin/env python
# coding=utf-8

import config
from optparse import OptionParser
import sys
from database import PasswordDatabase

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-a', '--add-user', dest='addUser', action='store_true', default=False, help='adds new user. Requires --name and --password options.')
    parser.add_option('-r', '--remove-user', dest='removeUser', action='store_true', default=False, help='removes user. Requires --name option.')
    parser.add_option('-n', '--name', dest='name', default="", help='user\'s name.')
    parser.add_option('-p', '--password', dest='password', default="", help='user\'s password.')
    parser.add_option('-d', '--database', dest='database', help='database file to use (for storing users\' passwords. Default: users.db', default='users.db')
    parser.add_option('-l', '--list-users', dest='listUsers', help='list all users (only names).', default=False, action='store_true')
    options, args = parser.parse_args()

    if options.addUser and options.removeUser:
        print("You can't add and remove user at the same time.")
        sys.exit(1)
    if not (options.addUser or options.removeUser or options.listUsers):
        print("You have to use one of --add-user or --remove-user --list-users options.")
        sys.exit(1)
    config.databaseFile = options.database
    database = PasswordDatabase()
    if options.addUser:
        if not options.name or not options.password:
            print("Non-empty --name and --password options required.")
            sys.exit(2)
        database.addUser(options.name, options.password)
    elif options.removeUser:
        if not options.name:
            print("Non-empty --name option required.")
            sys.exit(2)
        database.removeUser(options.name)
    if options.listUsers:
        for user in database.getUsers():
            print(user)

