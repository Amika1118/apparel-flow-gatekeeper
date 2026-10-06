import sqlite3

def get_db():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()


get_db()