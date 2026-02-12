import re
import unicodedata
from urllib.parse import urlencode
from typing import Dict, Any
import uuid

def slugger(text: str) -> str:
    """Normalize text to slug format: lowercase, no accents, underscores."""
    if not text:
        return ""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    # Replace spaces with underscores
    text = re.sub(r'[\s+]', '_', text)
    # Remove non-alphanumeric (except underscore)
    text = re.sub(r'[^a-z0-9_]', '', text)
    return text

def normalize_utm(text: str) -> str:
    """Alias for slugger, used for UTM parameters."""
    return slugger(text)

def build_full_url(base_url: str, path: str, utm_params: Dict[str, Any], custom_params: Dict[str, Any]) -> str:
    """Construct full URL with optional path and query parameters."""
    # Build final base with optional path.
    final_base = base_url
    if path:
        if final_base.endswith("/") and path.startswith("/"):
            final_base = f"{final_base}{path[1:]}"
        elif not final_base.endswith("/") and not path.startswith("/"):
            final_base = f"{final_base}/{path}"
        else:
            final_base = f"{final_base}{path}"

    # Merge params and filter out None/empty values.
    merged = {}
    if utm_params:
        merged.update(utm_params)
    if custom_params:
        merged.update(custom_params)

    clean_params = {k: v for k, v in merged.items() if v is not None and v != ""}
    if not clean_params:
        return final_base

    query_string = urlencode(clean_params)
    separator = "&" if "?" in final_base else "?"
    return f"{final_base}{separator}{query_string}"

def generate_utm_id(db) -> str:
    """Generate a unique ID for a link (e.g. lnk_000123)."""
    # db is the supabase client
    if db is None:
        return f"lnk_{uuid.uuid4().hex[:6]}"

    try:
        # Fallback to simple read-write (low concurrency assumed)
        # Ideally, use an RPC or sequence in Postgres
        response = db.table("settings").select("count").eq("id", "link_counter").execute()
        
        if response.data and len(response.data) > 0:
            current_count = response.data[0]['count']
            new_count = current_count + 1
            # Update
            db.table("settings").update({"count": new_count}).eq("id", "link_counter").execute()
        else:
            new_count = 1
            # Insert first record
            db.table("settings").insert({"id": "link_counter", "count": new_count}).execute()
            
        return f"lnk_{new_count:06d}"

    except Exception as e:
        print(f"ID Generation failed: {e}")
        return f"lnk_{uuid.uuid4().hex[:6]}"
