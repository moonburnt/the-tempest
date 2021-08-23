from flask import current_app, g
import pymongo
import logging

log = logging.getLogger(__name__)


# All of these are meant to be casted via "with app.context()", unless chained
def get_client():
    """Get connection to database from current flask application"""
    if "mongo_client" not in g:
        address = current_app.config["MONGODB_ADDRESS"]
        g.mongo_client = pymongo.MongoClient(address)
        log.debug(f"Successfully connected to mongodb on {address}")

    return g.mongo_client


def get_db():
    """Get database from current client"""
    if "db" not in g:
        client = get_client()
        g.db = client[current_app.config["DATABASE_NAME"]]

    return g.db


def close_connection():
    """Close connection to mongodb"""
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()
        # Ensuring related db will be removed too
        g.pop("db", None)
        log.debug("Successfully closed connection to database")
