from flask import current_app, g
import pymongo
import logging

log = logging.getLogger(__name__)

# All of these are meant to be casted via "with app.context()", unless chained
def get_client() -> pymongo.mongo_client.MongoClient:
    """Get connection to database from current flask application"""
    if "mongo_client" not in g:
        address = current_app.config["MONGODB_ADDRESS"]
        g.mongo_client = pymongo.MongoClient(address)
        log.debug(f"Successfully connected to mongodb on {address}")

    return g.mongo_client


def get_db() -> pymongo.database.Database:
    """Get database from current client"""
    if "db" not in g:
        client = get_client()
        g.db = client[current_app.config["DATABASE_NAME"]]

    return g.db


def get_users_collection() -> pymongo.collection.Collection:
    """Get collection named 'users' from current db"""
    if "users_collection" not in g:
        db = get_db()
        g.users_collection = db["users"]

    return g.users_collection


def get_files_collection() -> pymongo.collection.Collection:
    """Get collection named 'files' from current db"""
    if "files_collection" not in g:
        db = get_db()
        g.files_collection = db["files"]

    return g.files_collection


def get_users_amount() -> int:
    """Get amount of entries in 'users' collection of current db"""
    return get_users_collection().count()


def get_files_amount() -> int:
    """Get amount of entries in 'files' collection of current db"""
    return get_files_collection().count()


def initialize_files_indexes():
    """Initialize all required indexes for 'files' collection of current db"""
    # There should be no issues with casting it multiple times on same db, since
    # according to mongodb docs indexes only get created if they didnt exist already

    col = get_files_collection()

    # For now we only need index to sort files from older to newer
    col.create_index(
        [("uploaded", pymongo.ASCENDING)],
        name="Query for files, from oldest to newest",
    )

    # And maybe also to get files that has been accessed eternity ago
    col.create_index(
        [("last_access", pymongo.ASCENDING)],
        name="Query for files last access time, from oldest to newest",
    )


def get_user_files(user_id: str) -> pymongo.cursor.Cursor:
    """Get files uploaded by specific user"""

    return get_files_collection().find({"uploader": user_id})


def close_connection():
    """Close connection to mongodb"""
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()
        # Ensuring other related entries will be removed too
        g.pop("db", None)
        g.pop("files_collection", None)
        g.pop("users_collection", None)
        log.debug("Successfully closed connection to database")
