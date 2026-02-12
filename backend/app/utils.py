import re
import unicodedata
from urllib.parse import urlencode
from typing import Dict, Any, Tuple, Optional
import uuid

def slugger(text: str) -> str:
    """Normalize text to slug format: lowercase, no accents, underscores/hyphens."""
    if not text:
        return ""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    # Replace spaces with underscores
    text = re.sub(r'[\s+]', '_', text)
    # Keep alphanumeric plus underscore/hyphen
    text = re.sub(r'[^a-z0-9_-]', '', text)
    # Collapse repeated separators
    text = re.sub(r'_+', '_', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('_-')
    return text

def normalize_utm(text: str) -> str:
    """Alias for slugger, used for UTM parameters."""
    return slugger(text)

def normalize_campaign(text: str) -> str:
    """Normalize campaign and canonicalize final date token to mm-yy when possible."""
    campaign = slugger(text)
    if not campaign:
        return ""

    parts = campaign.split("_")
    if not parts:
        return campaign

    last = parts[-1]
    if re.fullmatch(r"\d{4}", last):
        # 0124 -> 01-24
        parts[-1] = f"{last[:2]}-{last[2:]}"
    elif re.fullmatch(r"\d{2}_\d{2}", last):
        parts[-1] = last.replace("_", "-")

    return "_".join(parts)

def normalize_utm_term(text: str) -> str:
    """Normalize utm_term and canonicalize trailing date token to dd-mm-yyyy."""
    term = slugger(text)
    if not term:
        return ""

    parts = term.split("_")
    if not parts:
        return term

    last = parts[-1]
    if re.fullmatch(r"\d{8}", last):
        parts[-1] = f"{last[:2]}-{last[2:4]}-{last[4:]}"
    elif re.fullmatch(r"\d{2}-\d{2}-\d{4}", last):
        parts[-1] = last

    return "_".join(parts)

def sanitize_custom_params(custom_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Drop reserved tracking keys from custom params to enforce governance."""
    if not custom_params:
        return {}

    reserved = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "utm_id",
        "src",
        "sck",
        "xcode",
    }
    out: Dict[str, Any] = {}
    for key, value in custom_params.items():
        if key.lower() in reserved:
            continue
        out[key] = value
    return out

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
    if custom_params:
        merged.update(custom_params)
    if utm_params:
        merged.update(utm_params)

    clean_params = {k: v for k, v in merged.items() if v is not None and v != ""}
    if not clean_params:
        return final_base

    query_string = urlencode(clean_params)
    separator = "&" if "?" in final_base else "?"
    return f"{final_base}{separator}{query_string}"

def build_tracking_params(
    link_type: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
    utm_term: str,
    utm_id: str
) -> Tuple[Dict[str, Any], Optional[str], Optional[str], Optional[str]]:
    """Build query params and vendas-only derived fields."""
    params = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
    }

    src = None
    sck = None
    xcode = None

    if link_type == "vendas":
        # For vendas links, utm_id is represented as xcode in query string.
        xcode = utm_id
        src = f"{utm_source}_{utm_content}".strip("_")
        sck = utm_medium
        params.update({
            "xcode": xcode,
            "src": src,
            "sck": sck,
        })
    else:
        params["utm_id"] = utm_id

    return params, src, sck, xcode

def generate_utm_id(db) -> str:
    """Generate a unique ID for a link (e.g. lnk_000123)."""
    # db is the supabase client
    if db is None:
        return f"lnk_{uuid.uuid4().hex[:6]}"

    try:
        # Prefer atomic increment via Postgres RPC to avoid collisions in concurrent requests.
        rpc_response = db.rpc("increment_link_counter", {"row_id": "link_counter"}).execute()
        if rpc_response.data is not None:
            if isinstance(rpc_response.data, list) and len(rpc_response.data) > 0:
                new_count = int(rpc_response.data[0])
            else:
                new_count = int(rpc_response.data)
            return f"lnk_{new_count:06d}"

        # Fallback path if RPC is unavailable.
        response = db.table("settings").select("count").eq("id", "link_counter").execute()
        if response.data and len(response.data) > 0:
            current_count = response.data[0]["count"]
            new_count = current_count + 1
            db.table("settings").update({"count": new_count}).eq("id", "link_counter").execute()
        else:
            new_count = 1
            db.table("settings").insert({"id": "link_counter", "count": new_count}).execute()

        return f"lnk_{new_count:06d}"

    except Exception as e:
        print(f"ID Generation failed: {e}")
        return f"lnk_{uuid.uuid4().hex[:6]}"
