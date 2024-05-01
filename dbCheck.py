import sqlite3

def dbConnectionUsers():
    con=sqlite3.connect('data/users.db')
    return con

with dbConnectionUsers() as con:
    c=con.cursor()
    c.execute('SELECT * FROM users')
    res=c.fetchall()
    if res:
        print(res)
    else:
        print('fail')