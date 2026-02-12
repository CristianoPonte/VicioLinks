import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Global Supabase client
supabase: Client = None

def get_db():
    global supabase
    if supabase is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if url and key:
            try:
                supabase = create_client(url, key)
                print(f"Connected to Supabase: {url}")
            except Exception as e:
                print(f"Failed to connect to Supabase: {e}")
                raise e
        else:
            print("Supabase credentials not found (SUPABASE_URL, SUPABASE_KEY)")
            # For strict migration, we might want to fail here, but let's keep it robust
            # or maybe fallback to local if needed? Ideally we want Supabase.
            if os.environ.get("UseLocalDB", "False") == "True":
                 return LocalStorage()
            # If not explicitly local and no creds, return None or error
            return None 

    return supabase

# Keep LocalStorage for fallback or specific dev needs if requested, 
# but primarily we move to Supabase.
class LocalStorage:
    # ... (Keep existing implementation if strictly needed for fallback, 
    # but the goal is to MIGRATE. Let's comment/remove to force migration)
    pass
