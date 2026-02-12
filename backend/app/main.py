from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import os

from .models import Link, LinkCreate, Launch, SourceConfig, Product, Turma, LaunchType, Token, User, UserInDB, UserCreate
from .utils import normalize_utm, build_full_url, generate_utm_id, slugger
from .database import get_db
from .auth import authenticate_user, create_access_token, get_current_active_user, require_admin, require_editor, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from fastapi.security import OAuth2PasswordRequestForm

app = FastAPI(title="Link Hub API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_path = os.path.join(BASE_DIR, "frontend")

@app.on_event("startup")
async def startup_event():
    """Seed initial data if database is empty."""
    db = get_db()
    
    if db is None:
        print("Skipping seeding: Database connection not available.")
        return

    # helper to check if table is empty
    def is_empty(table_name):
        try:
            res = db.table(table_name).select("*", count="exact").limit(1).execute()
            return res.count == 0
        except Exception as e:
            print(f"Error checking table {table_name}: {e}")
            return True # Assume empty on error to be safe? Or False to avoid overwrite? 
            # If table doesn't exist, this will error. User needs to run SQL.
            return True

    try:
        # Always upsert source configs to ensure they match the codebase (utm_list.md)
        print("Seeding/Updating source_configs...")
        # New Structure: Source -> { config: { mediums: [], contents: [], ... } }
        initial_sources = [
            {
                "slug": "email", 
                "name": "Email", 
                "config": {
                    "mediums": [{"slug": "newsletter", "name": "Newsletter"}, {"slug": "marketing", "name": "Marketing"}],
                    "contents": [{"slug": "lista_atual", "name": "Lista Atual"}, {"slug": "lista_antiga", "name": "Lista Antiga"}, {"slug": "ex_alunos", "name": "Ex-Alunos"}],
                    "term_config": "standard",
                    "required_fields": ["date"]
                }
            },
            {
                "slug": "whatsapp", 
                "name": "WhatsApp", 
                "config": {
                    "mediums": [{"slug": "api_disparos", "name": "API Disparos"}, {"slug": "api_sequencias", "name": "API Sequências"}, {"slug": "grupos", "name": "Grupos"}],
                    "contents": [{"slug": "grupos_antigos", "name": "Grupos Antigos"}, {"slug": "grupos_atuais", "name": "Grupos Atuais"}, {"slug": "lista_lanc_atual", "name": "Lista Lançamento Atual"}],
                    "term_config": "standard",
                    "required_fields": ["date"]
                }
            },
            {
                "slug": "site", 
                "name": "Site", 
                "config": {
                    "mediums": [{"slug": "institucional", "name": "Institucional"}, {"slug": "plataforma_vde1f", "name": "Plat. VDE1F"}],
                    "contents": [{"slug": "banner", "name": "Banner"}, {"slug": "cupom_exclusivo", "name": "Cupom Exclusivo"}],
                    "term_config": "no_date",
                    "required_fields": []
                }
            },
            {
                "slug": "instagram", 
                "name": "Instagram", 
                "config": {
                    "mediums": [{"slug": "feed_mc", "name": "Feed MC"}, {"slug": "story_mc", "name": "Story MC"}, {"slug": "direct_mc", "name": "Direct MC"}, {"slug": "bio_link", "name": "Link na Bio"}],
                    "contents": [{"slug": "insta_vicio", "name": "Insta Vício"}, {"slug": "insta_vde", "name": "Insta VDE"}],
                    "term_config": "standard",
                    "required_fields": []
                }
            },
             {
                "slug": "google", 
                "name": "Google", 
                "config": {
                    "mediums": [{"slug": "cpc", "name": "CPC"}, {"slug": "display", "name": "Display"}, {"slug": "search", "name": "Search"}],
                    "contents": [{"slug": "keyword", "name": "Palavra Chave"}, {"slug": "banner", "name": "Banner Anúncio"}],
                    "term_config": "standard",
                    "required_fields": ["term"]
                }
            },
            {
                "slug": "youtube", 
                "name": "YouTube", 
                "config": {
                    "mediums": [{"slug": "canal_vicio", "name": "Canal Vício"}, {"slug": "canal_concursos", "name": "Canal Concursos"}],
                    "contents": [{"slug": "descricao_video", "name": "Descrição Vídeo"}, {"slug": "qrcode", "name": "QR Code"}, {"slug": "link_live", "name": "Link Live"}],
                    "term_config": "manual",
                    "required_fields": []
                }
            },
            {
                "slug": "meta", 
                "name": "Meta", 
                "config": {
                    "mediums": [{"slug": "facebook_ads", "name": "Facebook Ads"}, {"slug": "instagram_ads", "name": "Instagram Ads"}],
                    "contents": [{"slug": "static", "name": "Imagem Estática"}, {"slug": "video", "name": "Vídeo"}, {"slug": "carousel", "name": "Carrossel"}],
                    "term_config": "standard",
                    "required_fields": []
                }
            }
        ]
        for s in initial_sources:
            db.table("source_configs").upsert(s).execute()

        if is_empty("products"):
            db.table("products").upsert({"slug": "vde1f", "nome": "VDE1F"}).execute()
        
        if is_empty("turmas"):
            db.table("turmas").upsert({"slug": "120d", "nome": "120d"}).execute()
            
        if is_empty("launch_types"):
            db.table("launch_types").upsert({"slug": "passariano", "nome": "Passariano"}).execute()
            db.table("launch_types").upsert({"slug": "evento", "nome": "Evento"}).execute()

        if is_empty("users"):
            print("Seeding users...")
            users = [
                {"username": "admin", "password": "admin123", "role": "admin"},
                {"username": "user", "password": "user123", "role": "user"},
                {"username": "viewer", "password": "viewer123", "role": "viewer"}
            ]
            for u in users:
                hashed_pw = get_password_hash(u["password"])
                user_in_db = UserInDB(username=u["username"], role=u["role"], hashed_password=hashed_pw)
                # Store using dict() to serialize properly
                db.table("users").upsert(user_in_db.dict()).execute()
    except Exception as e:
        print(f"Seeding failed: {e}")

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# User Management (Admin Only)
@app.get("/users", response_model=List[User])
async def get_all_users(current_user: User = Depends(require_admin)):
    db = get_db()
    res = db.table("users").select("*").execute()
    return [User(**u) for u in res.data]

@app.post("/users", response_model=User)
async def create_new_user(user_data: UserCreate, current_user: User = Depends(require_admin)):
    db = get_db()
    # Check if user already exists
    res = db.table("users").select("username").eq("username", user_data.username).execute()
    if res.data and len(res.data) > 0:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = get_password_hash(user_data.password)
    user_in_db = UserInDB(
        username=user_data.username,
        role=user_data.role,
        disabled=user_data.disabled,
        hashed_password=hashed_pw
    )
    db.table("users").upsert(user_in_db.dict()).execute()
    return User(**user_in_db.dict())

@app.put("/users/{username}", response_model=User)
async def update_user(username: str, user_data: UserCreate, current_user: User = Depends(require_admin)):
    db = get_db()
    res = db.table("users").select("username").eq("username", username).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_pw = get_password_hash(user_data.password)
    user_in_db = UserInDB(
        username=username,
        role=user_data.role,
        disabled=user_data.disabled,
        hashed_password=hashed_pw
    )
    db.table("users").update(user_in_db.dict()).eq("username", username).execute()
    return User(**user_in_db.dict())

@app.delete("/users/{username}")
async def delete_user(username: str, current_user: User = Depends(require_admin)):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super-admin")
    db = get_db()
    db.table("users").delete().eq("username", username).execute()
    return {"status": "deleted"}

@app.get("/launches", response_model=List[dict])
async def get_launches(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    res = db.table("launches").select("*").execute()
    return res.data

@app.post("/launches")
async def create_launch(data: Launch, current_user: User = Depends(require_admin)):
    db = get_db()
    db.table("launches").upsert(data.dict()).execute()
    return data

@app.delete("/launches/{slug}")
async def delete_launch(slug: str, current_user: User = Depends(require_admin)):
    db = get_db()
    db.table("launches").delete().eq("slug", slug).execute()
    return {"status": "deleted"}

@app.get("/source-configs", response_model=List[dict])
async def get_source_configs(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    res = db.table("source_configs").select("*").execute()
    return res.data

@app.post("/source-configs")
async def create_source_config(data: SourceConfig, current_user: User = Depends(require_admin)):
    try:
        db = get_db()
        # Use model_dump() instead of deprecated dict()
        data_dict = data.model_dump(exclude_none=True, by_alias=True)
        print(f"[DEBUG] Upserting source config: {data_dict}")
        
        result = db.table("source_configs").upsert(data_dict).execute()
        print(f"[DEBUG] Upsert result: {result}")
        
        return data
    except Exception as e:
        print(f"[ERROR] Failed to upsert source config: {str(e)}")
        print(f"[ERROR] Data received: {data}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save source config: {str(e)}")

@app.delete("/source-configs/{slug}")
async def delete_source_config(slug: str):
    db = get_db()
    db.table("source_configs").delete().eq("slug", slug).execute()
    return {"status": "deleted"}

# Admin endpoints for Campaign Generator
@app.get("/products", response_model=List[Product])
async def get_products(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    res = db.table("products").select("*").execute()
    return [Product(**p) for p in res.data]

@app.post("/products")
async def create_product(data: Product, current_user: User = Depends(require_admin)):
    db = get_db()
    db.table("products").upsert(data.dict()).execute()
    return data

@app.get("/turmas", response_model=List[Turma])
async def get_turmas(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    res = db.table("turmas").select("*").execute()
    return [Turma(**t) for t in res.data]

@app.post("/turmas")
async def create_turma(data: Turma, current_user: User = Depends(require_admin)):
    db = get_db()
    db.table("turmas").upsert(data.dict()).execute()
    return data

@app.get("/launch-types", response_model=List[LaunchType])
async def get_launch_types(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    res = db.table("launch_types").select("*").execute()
    return [LaunchType(**l) for l in res.data]

@app.post("/launch-types")
async def create_launch_type(data: LaunchType, current_user: User = Depends(require_admin)):
    db = get_db()
    db.table("launch_types").upsert(data.dict()).execute()
    return data

@app.post("/links/generate", response_model=Link)
async def generate_link(data: LinkCreate, current_user: User = Depends(require_editor)):
    db = get_db()
    
    # 1. Normalization
    utm_source = normalize_utm(data.utm_source)
    utm_medium = normalize_utm(data.utm_medium)
    utm_campaign = normalize_utm(data.utm_campaign)
    utm_content = normalize_utm(data.utm_content or "")
    utm_term = normalize_utm(data.utm_term or "")

    # 2. Validation / Governance
    # (Simplified for now, UI handles most of it)
    if "email" in utm_medium and "date" in data.dynamic_fields:
        date_str = data.dynamic_fields["date"]
        utm_content = f"email_d{date_str.replace('-', '_')}"

    # 3. Generate Atomic ID
    utm_id = generate_utm_id(db)
    
    # 4. Handle Vendas Contract mapping
    src = None
    sck = None
    xcode = None
    
    utms = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
        "utm_id": utm_id
    }

    if data.link_type == "vendas":
        src = utm_medium
        sck = f"{utm_source}_{utm_content}".strip("_")
        xcode = utm_id
        utms.update({"src": src, "sck": sck, "xcode": xcode})
    
    # 5. Build Full URL
    full_url = build_full_url(data.base_url, data.path, utms, data.custom_params)
    
    # 6. Create Object
    link_obj = Link(
        id=utm_id,
        link_type=data.link_type,
        base_url=data.base_url,
        path=data.path or "",
        full_url=full_url,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        src=src,
        sck=sck,
        xcode=xcode,
        custom_params=data.custom_params,
        notes=data.notes,
        created_by="system_user",
        created_at=datetime.utcnow()
    )
    
    # 7. Save
    # Supabase uses 'insert' or 'upsert'. 'utm_id' is our primary key or strict unique.
    db.table("links").insert(link_obj.dict()).execute()
    
    # Audit logic
    db.table("audits").insert({
        "event_id": str(uuid.uuid4()),
        "link_id": utm_id,
        "actor": "system_user",
        "action": "create",
        "timestamp": datetime.utcnow().isoformat()
    }).execute()
        
    return link_obj

@app.get("/links", response_model=List[Link])
async def list_links(
    current_user: User = Depends(get_current_active_user),
    launch_id: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None
):
    db = get_db()
    
    query = db.table("links").select("*")
    
    if launch_id:
        query = query.eq("utm_campaign", launch_id)
    if utm_source:
        query = query.eq("utm_source", utm_source)
    if utm_medium:
        query = query.eq("utm_medium", utm_medium)
    
    # Sort by date
    res = query.order("created_at", desc=True).limit(100).execute()
    
    return [Link(**l) for l in res.data]

# Mount frontend at root last to avoid intercepting API routes
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
