import os
import json
from google.cloud import firestore
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv()

# In a real Cloud Run environment, it uses the service account identity.
db = None

class LocalStorage:
    """A simple JSON-based database for local development."""
    def __init__(self, filename="db.json"):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump({}, f)
    
    def _read(self) -> Dict[str, Any]:
        with open(self.filename, 'r') as f:
            return json.load(f)
    
    def _write(self, data: Dict[str, Any]):
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4, default=str)

    def collection(self, name: str):
        return LocalCollection(self, name)

class LocalCollection:
    def __init__(self, storage: LocalStorage, name: str):
        self.storage = storage
        self.name = name

    def _get_collection_data(self) -> Dict[str, Any]:
        data = self.storage._read()
        return data.get(self.name, {})

    def document(self, doc_id: str):
        return LocalDocument(self, doc_id)

    def stream(self):
        data = self._get_collection_data()
        return [LocalDocSnapshot(v) for v in data.values()]

    def add(self, data: Dict[str, Any]):
        import uuid
        doc_id = str(uuid.uuid4())
        self.document(doc_id).set(data)
        return doc_id

class LocalDocument:
    def __init__(self, collection: LocalCollection, doc_id: str):
        self.collection = collection
        self.doc_id = doc_id

    def set(self, data: Dict[str, Any]):
        all_data = self.collection.storage._read()
        if self.collection.name not in all_data:
            all_data[self.collection.name] = {}
        all_data[self.collection.name][self.doc_id] = data
        self.collection.storage._write(all_data)

    def get(self):
        data = self.collection._get_collection_data()
        doc = data.get(self.doc_id)
        return LocalDocSnapshot(doc)

    def delete(self):
        all_data = self.collection.storage._read()
        if self.collection.name in all_data and self.doc_id in all_data[self.collection.name]:
            del all_data[self.collection.name][self.doc_id]
            self.collection.storage._write(all_data)

class LocalDocSnapshot:
    def __init__(self, data):
        self._data = data
    
    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return self._data

def get_db():
    global db
    if db is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        # Only use Firestore if project_id is explicitly set and not 'local'
        if project_id and project_id != "local":
            try:
                db = firestore.Client(project=project_id)
                print(f"Connected to Firestore: {project_id}")
            except Exception as e:
                print(f"Firestore fallback to LocalStorage: {e}")
                db = LocalStorage()
        else:
            print("Using LocalStorage (db.json)")
            db = LocalStorage()
    return db
