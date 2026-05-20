"""
MongoDB connection and CRUD layer for TCM.io.

Credential resolution order:
  1. keys/mongo.txt  — local dev (line 1 = username, line 2 = password)
  2. st.secrets["MONGO_URI"] — Streamlit Cloud deployment
"""

import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi

_CLUSTER = "tcm-io.swnfirb.mongodb.net"
_APP_NAME = "TCM-io"
_DB_NAME  = "toccoa"
_COL_NAME = "deals"

STAGES   = ["Initial Review", "Term Sheet Out", "Due Diligence", "Approved", "Closed", "Dead"]
STATUSES = ["Active", "Inactive"]

_SEED_DEALS = [
    {"id": 1, "deal_name": "Peachtree Industrial Park",  "city": "Atlanta",    "stage": "Initial Review", "status": "Active"},
    {"id": 2, "deal_name": "Riverside Office Complex",   "city": "Savannah",   "stage": "Term Sheet Out", "status": "Active"},
    {"id": 3, "deal_name": "Midtown Retail Strip",       "city": "Atlanta",    "stage": "Closed",         "status": "Inactive"},
    {"id": 4, "deal_name": "Buckhead Mixed-Use",         "city": "Atlanta",    "stage": "Due Diligence",  "status": "Active"},
    {"id": 5, "deal_name": "Alpharetta Tech Campus",     "city": "Alpharetta", "stage": "Initial Review", "status": "Active"},
]


@st.cache_resource
def get_mongo_client() -> MongoClient:
    """Return a cached MongoClient.

    Tries keys/mongo.txt first (local dev). Falls back to st.secrets['MONGO_URI']
    when running on Streamlit Cloud where the keys/ directory doesn't exist.
    """
    try:
        with open("keys/mongo.txt", "r") as f:
            lines = f.read().splitlines()
        uri = f"mongodb+srv://{lines[0]}:{lines[1]}@{_CLUSTER}/?appName={_APP_NAME}"
    except FileNotFoundError:
        # Streamlit Cloud path — full URI stored as a secret
        uri = st.secrets["MONGO_URI"]

    return MongoClient(uri, server_api=ServerApi('1'))


def init_deals_collection() -> None:
    """Ensure the 'deals' collection exists in the 'toccoa' database.

    If the collection does not yet exist it is created and populated with
    seed data. If it already exists, it is left untouched.
    """
    try:
        db = get_mongo_client()[_DB_NAME]
        if _COL_NAME not in db.list_collection_names():
            db[_COL_NAME].insert_many(_SEED_DEALS)
    except Exception as e:
        st.error(f"Failed to initialise deals collection: {e}")


def get_all_deals(filters: dict = None) -> list[dict]:
    """Return all deal documents, optionally filtered.

    Args:
        filters: MongoDB filter dict, e.g. {"stage": "Initial Review"}.
                 Pass None or {} to return every document.

    Returns:
        List of deal dicts (MongoDB _id field excluded).
    """
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        query = filters or {}
        return list(col.find(query, {"_id": 0}).sort("id", 1))
    except Exception as e:
        st.error(f"Failed to fetch deals: {e}")
        return []


def update_deal(deal_id: int, **kwargs) -> bool:
    """Update a deal document by id with the provided fields.

    Args:
        deal_id: Integer id of the deal to update.
        **kwargs: Field names and new values, e.g. stage="Closed", city="Macon".

    Returns:
        True if a document was matched and updated, False otherwise.
    """
    if not kwargs:
        return False
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        result = col.update_one({"id": deal_id}, {"$set": kwargs})
        return result.matched_count > 0
    except Exception as e:
        st.error(f"Failed to update deal {deal_id}: {e}")
        return False
