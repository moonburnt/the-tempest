from flask import current_app, g
import pymongo
from dataclasses import dataclass
from datetime import datetime
import logging

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileInfo:
    # name of file on disk
    filename: str
    # name of file how its been received (after securing but without uuid4)
    original_name: str
    # not implemented yet #TODO
    # uploader: str
    # time of file's upload
    uploaded: datetime
    # when file was accessed the last time
    last_access: datetime


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
