import sqlite3

with sqlite3.connect('data/users.db') as con:
    with open('data/users.sql') as f:
        con.executescript(f.read())

with sqlite3.connect('data/data.db') as con:
    with open('data/data.sql') as f:
        con.executescript(f.read())