import re
import unicodedata
from typing import Dict, Any
from google.cloud import firestore

def slugger(text: str) -> str:
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Remove accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    # Replace spaces with _
    text = text.replace(' ', '_')
    # Remove special chars (keep a-z, 0-9, _, -)
    text = re.sub(r'[^a-z0-9_\-]', '', text)
    # Compact repetitions of _
    text = re.sub(r'_+', '_', text)
    # Trim _ from start/end
    text = text.strip('_')
    return text

def normalize_utm(text: str) -> str:
    return slugger(text)

def build_full_url(base_url: str, path: str, utms: Dict[str, str], custom_params: Dict[str, str]) -> str:
    # Ensure base_url doesn't end with slash if path starts with it
    base = base_url.rstrip('/')
    p = (path or "").lstrip('/')
    full_path = f"{base}/{p}" if p else base
    
    # Add UTMs/Params
    params = []
    # Merge UTMs and Custom Params
    all_params = {**utms, **custom_params}
    
    for k, v in all_params.items():
        if v:
            params.append(f"{k}={v}")
            
    if params:
        separator = "&" if "?" in full_path else "?"
        return f"{full_path}{separator}{'&'.join(params)}"
    
    return full_path

@firestore.transactional
def get_next_id_transaction(transaction, counter_ref):
    snapshot = counter_ref.get(transaction=transaction)
    if not snapshot.exists:
        count = 1
    else:
        count = snapshot.get("count") + 1
    
    transaction.set(counter_ref, {"count": count})
    return f"lnk_{count:06d}"

def generate_utm_id(db) -> str:
    # Handle LocalStorage (defined in database.py)
    if hasattr(db, 'filename'): # Simple way to check if it's our LocalStorage
        counter_ref = db.collection("settings").document("link_counter")
        snap = counter_ref.get()
        count = 1
        if snap:
            data = snap.to_dict()
            if data:
                count = data.get("count", 0) + 1
        counter_ref.set({"count": count})
        return f"lnk_{count:06d}"

    # Handle None
    if db is None:
        import uuid
        return f"lnk_{uuid.uuid4().hex[:6]}"
    
    # Handle Real Firestore
    try:
        counter_ref = db.collection("settings").document("link_counter")
        transaction = db.transaction()
        return get_next_id_transaction(transaction, counter_ref)
    except Exception as e:
        print(f"Transaction failed, falling back to simple ID: {e}")
        import uuid
        return f"lnk_{uuid.uuid4().hex[:6]}"
