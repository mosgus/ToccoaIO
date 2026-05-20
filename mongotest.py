"""
MongoDB CRUD tester — interactive CLI for learning MongoDB operations.
Run: python mongotest.py
"""

from pymongo import MongoClient
from pymongo.server_api import ServerApi


# --- Connection ---

def connect():
    with open("keys/mongo.txt", "r") as f:
        lines = f.read().splitlines()
    uri = f"mongodb+srv://{lines[0]}:{lines[1]}@tcm-io.swnfirb.mongodb.net/?appName=TCM-io"
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client


# --- DB / Collection Selection ---

def select_db(client) -> tuple:
    """Prompt user to pick an existing database or name a new one.
    Returns (db_name, db).
    Note: MongoDB creates a new database on the first write — selecting a new
    name here does nothing until a document is inserted.
    """
    existing = [n for n in client.list_database_names() if n not in ("admin", "local", "config")]
    print("\n  Existing databases:")
    for i, name in enumerate(existing, 0):
        print(f"    {i}. {name}")
    print("    n. New database")

    choice = input("  Select '#' or 'n': ").strip().lower()
    if choice == "n":
        db_name = input("  New database name: ").strip()
        print(f"  ('{db_name}' will be created on first insert)")
    elif choice.isdigit() and 0 <= int(choice) <= len(existing):
        db_name = existing[int(choice)]
    else:
        print("  Invalid — defaulting to first database.")
        db_name = existing[0] if existing else "tcm_db"

    return db_name, client[db_name]


def select_collection(db) -> tuple:
    """Prompt user to pick an existing collection or name a new one.
    Returns (collection_name, collection).
    Note: MongoDB creates a new collection on the first write.
    """
    existing = db.list_collection_names()
    print(f"\n  Collections in '{db.name}':")
    if existing:
        for i, name in enumerate(existing, 1):
            print(f"    {i}. {name}")
    else:
        print("    (none yet)")
    print("    n. New collection")

    choice = input("  Select number or 'n': ").strip().lower()
    if choice == "n":
        col_name = input("  New collection name: ").strip()
        print(f"  ('{col_name}' will be created on first insert)")
    elif choice.isdigit() and existing and 1 <= int(choice) <= len(existing):
        col_name = existing[int(choice) - 1]
    else:
        print("  Invalid — defaulting to first collection (or 'tester').")
        col_name = existing[0] if existing else "tester"

    return col_name, db[col_name]


# --- CRUD Operations ---

def list_all(col):
    """Fetch and print every document, sorted by id."""
    docs = list(col.find({}, {"_id": 0}).sort("id", 1))
    if not docs:
        print("  (collection is empty)")
    for doc in docs:
        print(f"  {doc}")
    print(f"  [{len(docs)} document(s)]")


def insert_one_doc(col):
    """Insert a single new document with a user-supplied id and value."""
    try:
        doc_id = int(input("  id (integer): "))
    except ValueError:
        print("  ✗ id must be an integer.")
        return
    value = input("  value: ")
    col.insert_one({"id": doc_id, "value": value})
    print(f"  ✓ Inserted {{id: {doc_id}, value: '{value}'}}")


def update_one_doc(col):
    """Update the value field of a document matched by id."""
    try:
        doc_id = int(input("  id to update: "))
    except ValueError:
        print("  ✗ id must be an integer.")
        return
    new_value = input("  new value: ")
    result = col.update_one({"id": doc_id}, {"$set": {"value": new_value}})
    if result.matched_count:
        print(f"  ✓ Updated id {doc_id} → '{new_value}'")
    else:
        print(f"  ✗ No document found with id {doc_id}")


def delete_one_doc(col):
    """Delete a single document matched by id."""
    try:
        doc_id = int(input("  id to delete: "))
    except ValueError:
        print("  ✗ id must be an integer.")
        return
    result = col.delete_one({"id": doc_id})
    if result.deleted_count:
        print(f"  ✓ Deleted id {doc_id}")
    else:
        print(f"  ✗ No document found with id {doc_id}")


def find_by_value(col):
    """Query documents whose value contains a search string (case-insensitive regex)."""
    term = input("  search value contains: ")
    # $regex with $options 'i' = case-insensitive — equivalent to SQL LIKE '%term%'
    docs = list(col.find({"value": {"$regex": term, "$options": "i"}}, {"_id": 0}))
    if not docs:
        print("  (no matches)")
    for doc in docs:
        print(f"  {doc}")


def bulk_insert(col):
    """Insert multiple documents at once (comma-separated values, auto-increments id)."""
    raw = input("  values (comma-separated, e.g. alpha,beta,gamma): ")
    values = [v.strip() for v in raw.split(",") if v.strip()]
    if not values:
        print("  ✗ No values provided.")
        return
    # Start id after current max to avoid collisions
    max_doc = col.find_one(sort=[("id", -1)])
    next_id = (max_doc["id"] + 1) if max_doc else 1
    docs = [{"id": next_id + i, "value": v} for i, v in enumerate(values)]
    col.insert_many(docs)
    print(f"  ✓ Inserted {len(docs)} document(s): {[d['id'] for d in docs]}")

def count_docs(col):
    """Print total document count."""
    n = col.count_documents({})
    print(f"  Total documents: {n}")


def drop_collection(col):
    """Drop the entire collection. Irreversible."""
    confirm = input(f"  Drop collection '{col.name}' entirely? This cannot be undone. (y/n): ")
    if confirm.lower() != "y":
        print("  Cancelled.")
        return
    col.drop()
    print(f"  ✓ Collection '{col.name}' dropped.")


# --- CLI ---

def build_menu(db_name, col_name) -> str:
    return f"""
  db: {db_name}  |  collection: {col_name}
  ─────────────────────────────────────
  1  List all        2  Insert one
  3  Update by id    4  Delete by id
  5  Find by value   6  Bulk insert
  7  Count           8  Drop collection
  s  Switch db / collection
  q  Quit
"""


ACTIONS = {
    "1": list_all,
    "2": insert_one_doc,
    "3": update_one_doc,
    "4": delete_one_doc,
    "5": find_by_value,
    "6": bulk_insert,
    "7": count_docs,
    "8": drop_collection,
}

if __name__ == "__main__":
    print("Connecting to MongoDB...")
    client = connect()
    try:
        client.admin.command('ping')
        print("✓ Connected.")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        client.close()
        exit(1)

    db_name, db = select_db(client)
    col_name, col = select_collection(db)

    while True:
        print(build_menu(db_name, col_name))
        choice = input("  Select: ").strip().lower()

        if choice == "q":
            break
        elif choice == "s":
            db_name, db = select_db(client)
            col_name, col = select_collection(db)
        elif choice in ACTIONS:
            print()
            ACTIONS[choice](col)
        else:
            print("  ✗ Invalid option.")

    client.close()
    print("Disconnected.")
