import sqlite3

import sqlalchemy.orm
from sqlalchemy.orm.session import sessionmaker
import config as cfg
from sqlalchemy import create_engine,event


def get_db():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()

class Engine:
    connect_args = {}

    if cfg.Settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        cfg.Settings.DATABASE_URL,
        connect_args=connect_args,
    )

    if cfg.Settings.DATABASE_URL.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def on_connet(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()


    session_local = sessionmaker(bind=engine,autoflush=False,autocommit=False)

    class base:
        sqlalchemy
