from app.database import get_db
from app.models import Launch, LinkType
from datetime import datetime

def seed():
    db = get_db()
    if not db:
        print("Firestore not available. Skipping seed.")
        return

    # 1. Launches
    launches = [
        {"slug": "enem_intensivo_2026", "nome": "Enem Intensivo 2026", "owner": "Marketing", "status": "active"},
        {"slug": "black_friday_2025", "nome": "Black Friday 2025", "owner": "Sales", "status": "active"}
    ]
    for l in launches:
        db.collection("launches").document(l["slug"]).set(l)

    # 2. Link Types
    types = [
        {
            "canal": "email",
            "subtipo": "email_disparo",
            "required_fields": ["date"],
            "allowed_sources": ["activecampaign"],
            "allowed_mediums": ["email"]
        },
        {
            "canal": "whatsapp",
            "subtipo": "whatsapp_broadcast",
            "required_fields": [],
            "allowed_sources": ["whatsapp"],
            "allowed_mediums": ["messaging"]
        },
        {
            "canal": "instagram",
            "subtipo": "instagram_stories",
            "required_fields": ["pos"],
            "allowed_sources": ["instagram"],
            "allowed_mediums": ["social"]
        }
    ]
    for t in types:
        doc_id = f"{t['canal']}_{t['subtipo']}"
        db.collection("link_types").document(doc_id).set(t)

    print("Seed complete!")

if __name__ == "__main__":
    seed()
