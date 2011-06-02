#!/usr/bin/env python
# coding=utf-8

import config
from optparse import OptionParser
import sys
from database import PasswordDatabase

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-a', '--add-hidden-server', dest='addHS', action='store_true', default=False, help='adds new HiddenServer. Requires --name and --password options.')
    parser.add_option('-r', '--remove-hidden-server', dest='removeHS', action='store_true', default=False, help='removes HiddenServer. Requires --name option.')
    parser.add_option('-n', '--name', dest='name', default="", help='HiddenServer\'s name.')
    parser.add_option('-p', '--password', dest='password', default="", help='HiddenServer\'s password.')
    parser.add_option('-d', '--database', dest='database', help='database file to use (for storing HiddenServer\'s passwords. Default: hidden-servers.db', default='hidden-servers.db')
    parser.add_option('-l', '--list-hidden-servers', dest='listHS', help='list all HiddenServers (only names).', default=False, action='store_true')
    options, args = parser.parse_args()

    if options.addHS and options.removeHS:
        print("You can't add and remove HiddenServers at the same time.")
        sys.exit(1)
    if not (options.addHS or options.removeHS or options.listHS):
        print("You have to use one of --add-hidden-server or --remove-hidden-server --list-hidden-servers options.")
        sys.exit(1)
    config.databaseFile = options.database
    database = PasswordDatabase()
    if options.addHS:
        if not options.name or not options.password:
            print("Non-empty --name and --password options required.")
            sys.exit(2)
        database.addUser(options.name, options.password)
    elif options.removeHS:
        if not options.name:
            print("Non-empty --name option required.")
            sys.exit(2)
        database.removeUser(options.name)
    if options.listHS:
        for hs in database.getUsers():
            print(hs)

