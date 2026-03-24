from pymongo import MongoClient
import modules.state as state

mongo_client = None
db = None
settings_collection = None
users_collection = None
sent_movies_collection = None
custom_sent_links_collection = None

def init_db():
    global mongo_client, db, settings_collection, users_collection, sent_movies_collection, custom_sent_links_collection
    from config import MONGO_URI, DB_NAME, SETTINGS_COLLECTION, USERS_COLLECTION
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    settings_collection = db[SETTINGS_COLLECTION]
    users_collection = db[USERS_COLLECTION]
    sent_movies_collection = db['sent_movies']
    custom_sent_links_collection = db['custom_sent_links']
    # Ensure detail_url is indexed for fast duplicate check
    sent_movies_collection.create_index("detail_url", unique=True)
    # Ensure custom link dedup is fast and unique per channel+url
    custom_sent_links_collection.create_index([("channel_id", 1), ("url", 1)], unique=True)

def load_state():
    doc = settings_collection.find_one({"_id": "bot_settings"})
    if doc:
        state.rss_sources[:] = doc.get("rss_sources", [])
        state.last_sent_ids.clear()
        state.last_sent_ids.update(doc.get("last_sent_ids", {}))
        state.bot_paused = doc.get("bot_paused", False)
        state.custom_channels[:] = doc.get("custom_channels", [])
    else:
        save_state()

def save_state():
    settings_collection.update_one(
        {"_id": "bot_settings"},
        {"$set": {
            "rss_sources": state.rss_sources,
            "last_sent_ids": state.last_sent_ids,
            "bot_paused": state.bot_paused,
            "custom_channels": state.custom_channels
        }},
        upsert=True
    )

# DEDUPLICATION HELPERS

def get_sent_movies_collection():
    if sent_movies_collection is not None:
        return sent_movies_collection
    # fallback if init_db not called yet
    from config import MONGO_URI, DB_NAME
    client = MongoClient(MONGO_URI)
    db_ref = client[DB_NAME]
    return db_ref['sent_movies']

def get_custom_sent_links_collection():
    if custom_sent_links_collection is not None:
        return custom_sent_links_collection
    # fallback if init_db not called yet
    from config import MONGO_URI, DB_NAME
    client = MongoClient(MONGO_URI)
    db_ref = client[DB_NAME]
    return db_ref['custom_sent_links']

def already_sent(detail_url, title=None):
    """
    Checks if a movie with this detail_url (or optionally title) has already been sent.
    """
    coll = get_sent_movies_collection()
    if title:
        return coll.find_one({"$or": [{"detail_url": detail_url}, {"title": title}]}) is not None
    else:
        return coll.find_one({"detail_url": detail_url}) is not None

def mark_as_sent(detail_url, title, **extra_data):
    """
    Marks this detail_url as sent (with extra info) for deduplication.
    """
    coll = get_sent_movies_collection()
    doc = {
        "detail_url": detail_url,
        "title": title,
        **extra_data
    }
    coll.update_one({"detail_url": detail_url}, {"$set": doc}, upsert=True)

# Custom channel URL dedup helpers

def custom_url_already_sent(channel_id, url):
    """
    Returns True if the given URL has already been sent to the specified custom channel.
    """
    coll = get_custom_sent_links_collection()
    return coll.find_one({"channel_id": channel_id, "url": url}) is not None

def mark_custom_url_sent(channel_id, url, **extra_data):
    """
    Marks the given URL as sent to the specified custom channel.
    """
    coll = get_custom_sent_links_collection()
    doc = {
        "channel_id": channel_id,
        "url": url,
        **extra_data
    }
    coll.update_one({"channel_id": channel_id, "url": url}, {"$set": doc}, upsert=True)
