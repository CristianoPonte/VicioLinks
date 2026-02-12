from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Launch(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    slug: str
    nome: str
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    owner: str
    status: str = "active"

class Product(BaseModel):
    slug: str
    nome: str

class Turma(BaseModel):
    slug: str
    nome: str

class LaunchType(BaseModel):
    slug: str # evento, passariano, perpetuo
    nome: str

class MediumItem(BaseModel):
    slug: str
    name: str

class ContentItem(BaseModel):
    slug: str
    name: str

class SourceConfigData(BaseModel):
    mediums: List[MediumItem] = Field(default_factory=list)
    contents: List[ContentItem] = Field(default_factory=list)
    term_config: str = "standard"
    required_fields: List[str] = Field(default_factory=list)

class SourceConfig(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    slug: str # e.g., "email", "whatsapp", "site"
    name: str # e.g., "Email", "WhatsApp"
    config: Optional[SourceConfigData] = None

class LinkCreate(BaseModel):
    link_type: str = "captacao" # captacao or vendas
    base_url: str
    path: Optional[str] = ""
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    custom_params: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None
    dynamic_fields: Dict[str, Any] = Field(default_factory=dict)
    # For Vendas mapping
    src: Optional[str] = None
    sck: Optional[str] = None
    xcode: Optional[str] = None

class Link(BaseModel):
    id: str # utm_id (lnk_000001)
    link_type: str # captacao or vendas
    base_url: str
    path: str
    full_url: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    # For Vendas
    src: Optional[str] = None
    sck: Optional[str] = None
    xcode: Optional[str] = None
    custom_params: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_by: str
    created_at: datetime
    status: str = "active"

class User(BaseModel):
    username: str
    role: str = "user" # admin, user, viewer
    disabled: Optional[bool] = False

class UserCreate(User):
    password: str

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
