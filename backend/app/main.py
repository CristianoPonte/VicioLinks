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
    
    # helper to check if collection is empty
    def is_empty(col_name):
        return len(list(db.collection(col_name).stream())) == 0

    if is_empty("source_configs"):
        print("Seeding source_configs...")
        initial_sources = [
            {
                "slug": "email", "name": "Email", "term_config": "standard", "required_fields": ["date"],
                "mediums": [
                    {"slug": "newsletter", "name": "Newsletter", "allowed_contents": ["lista_atual", "lista_antiga"]},
                    {"slug": "marketing", "name": "Marketing", "allowed_contents": ["ex_alunos", "engajados"]}
                ]
            },
            {
                "slug": "whatsapp", "name": "WhatsApp", "term_config": "standard", "required_fields": ["date"],
                "mediums": [
                    {"slug": "grupos", "name": "Grupos", "allowed_contents": ["grupos_antigos", "grupos_atuais"]},
                    {"slug": "api", "name": "API", "allowed_contents": ["ex-alunos", "lista_lanc_atual"]}
                ]
            },
            {
                "slug": "site", "name": "Site", "term_config": "no_date", "required_fields": [],
                "mediums": [
                    {"slug": "site_institucional", "name": "Institucional", "allowed_contents": ["banner", "cupom_exclusivo"]}
                ]
            }
        ]
        for s in initial_sources:
            db.collection("source_configs").document(s["slug"]).set(s)

    if is_empty("products"):
        db.collection("products").document("vde1f").set({"slug": "vde1f", "nome": "VDE1F"})
    
    if is_empty("turmas"):
        db.collection("turmas").document("120d").set({"slug": "120d", "nome": "120d"})
        
    if is_empty("launch_types"):
        db.collection("launch_types").document("passariano").set({"slug": "passariano", "nome": "Passariano"})
        db.collection("launch_types").document("evento").set({"slug": "evento", "nome": "Evento"})

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
            db.collection("users").document(u["username"]).set(user_in_db.dict())

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
    docs = db.collection("users").stream()
    return [User(**u.to_dict()) for u in docs]

@app.post("/users", response_model=User)
async def create_new_user(user_data: UserCreate, current_user: User = Depends(require_admin)):
    db = get_db()
    # Check if user already exists
    if db.collection("users").document(user_data.username).get().exists:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = get_password_hash(user_data.password)
    user_in_db = UserInDB(
        username=user_data.username,
        role=user_data.role,
        disabled=user_data.disabled,
        hashed_password=hashed_pw
    )
    db.collection("users").document(user_data.username).set(user_in_db.dict())
    return User(**user_in_db.dict())

@app.put("/users/{username}", response_model=User)
async def update_user(username: str, user_data: UserCreate, current_user: User = Depends(require_admin)):
    db = get_db()
    doc_ref = db.collection("users").document(username)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_pw = get_password_hash(user_data.password)
    user_in_db = UserInDB(
        username=username,
        role=user_data.role,
        disabled=user_data.disabled,
        hashed_password=hashed_pw
    )
    doc_ref.set(user_in_db.dict())
    return User(**user_in_db.dict())

@app.delete("/users/{username}")
async def delete_user(username: str, current_user: User = Depends(require_admin)):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super-admin")
    db = get_db()
    db.collection("users").document(username).delete()
    return {"status": "deleted"}

@app.get("/launches", response_model=List[dict])
async def get_launches(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    docs = db.collection("launches").stream()
    return [doc.to_dict() for doc in docs]

@app.post("/launches")
async def create_launch(data: Launch, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("launches").document(data.slug).set(data.dict())
    return data

@app.delete("/launches/{slug}")
async def delete_launch(slug: str, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("launches").document(slug).delete()
    return {"status": "deleted"}

@app.get("/source-configs", response_model=List[dict])
async def get_source_configs(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    docs = db.collection("source_configs").stream()
    return [doc.to_dict() for doc in docs]

@app.post("/source-configs")
async def create_source_config(data: SourceConfig, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("source_configs").document(data.slug).set(data.dict())
    return data

@app.delete("/source-configs/{slug}")
async def delete_source_config(slug: str):
    db = get_db()
    db.collection("source_configs").document(slug).delete()
    return {"status": "deleted"}

# Admin endpoints for Campaign Generator
@app.get("/products", response_model=List[Product])
async def get_products(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    docs = db.collection("products").stream()
    return [Product(**doc.to_dict()) for doc in docs]

@app.post("/products")
async def create_product(data: Product, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("products").document(data.slug).set(data.dict())
    return data

@app.get("/turmas", response_model=List[Turma])
async def get_turmas(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    docs = db.collection("turmas").stream()
    return [Turma(**doc.to_dict()) for doc in docs]

@app.post("/turmas")
async def create_turma(data: Turma, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("turmas").document(data.slug).set(data.dict())
    return data

@app.get("/launch-types", response_model=List[LaunchType])
async def get_launch_types(current_user: User = Depends(get_current_active_user)):
    db = get_db()
    docs = db.collection("launch_types").stream()
    return [LaunchType(**doc.to_dict()) for doc in docs]

@app.post("/launch-types")
async def create_launch_type(data: LaunchType, current_user: User = Depends(require_admin)):
    db = get_db()
    db.collection("launch_types").document(data.slug).set(data.dict())
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
    db.collection("links").document(utm_id).set(link_obj.dict())
    db.collection("audits").add({
        "event_id": str(uuid.uuid4()),
        "link_id": utm_id,
        "actor": "system_user",
        "action": "create",
        "timestamp": datetime.utcnow()
    })
        
    return link_obj

@app.get("/links", response_model=List[Link])
async def list_links(
    current_user: User = Depends(get_current_active_user),
    launch_id: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None
):
    db = get_db()
    docs = db.collection("links").stream()
    links = [Link(**doc.to_dict()) for doc in docs]
    
    # Simple tactical filtering in-memory for local development
    if launch_id:
        links = [l for l in links if l.utm_campaign == launch_id]
    if utm_source:
        links = [l for l in links if l.utm_source == utm_source]
    if utm_medium:
        links = [l for l in links if l.utm_medium == utm_medium]
    
    # Sort by date
    links.sort(key=lambda x: x.created_at, reverse=True)
    return links[:100]

# Mount frontend at root last to avoid intercepting API routes
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
