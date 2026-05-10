from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Body, UploadFile, File, Form, Header, Query
from fastapi.responses import JSONResponse, StreamingResponse
import csv
import io
import requests as http_requests
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

# ----------------- Setup -----------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'devsecret')
JWT_ALG = 'HS256'

# Object Storage (AWS S3)
import boto3
from botocore.exceptions import BotoCoreError, ClientError

APP_NAME = "agente-crm"
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB cap

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("S3_REGION", "eu-west-1"))
S3_BUCKET = os.environ.get("AWS_S3_BUCKET", os.environ.get("S3_BUCKET"))
# S3_ENDPOINT: se è un endpoint AWS standard, ignoralo (boto3 lo gestisce da solo tramite AWS_REGION)
_raw_endpoint = os.environ.get("S3_ENDPOINT", "").strip().strip("[]")
S3_ENDPOINT = None if (not _raw_endpoint or "amazonaws.com" in _raw_endpoint) else _raw_endpoint

_s3_client = None

def get_s3():
    global _s3_client
    if _s3_client:
        return _s3_client
    if not AWS_ACCESS_KEY_ID or not S3_BUCKET:
        return None
    kwargs = dict(
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT
    _s3_client = boto3.client("s3", **kwargs)
    return _s3_client
ALLOWED_EXT = {
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm",
    "avi": "video/x-msvideo", "mkv": "video/x-matroska",
}

def init_storage() -> bool:
    """Check S3 is configured."""
    return get_s3() is not None


def storage_put(path: str, data: bytes, content_type: str) -> dict:
    s3 = get_s3()
    if not s3:
        raise HTTPException(500, "Storage S3 non disponibile — controlla AWS_ACCESS_KEY_ID e AWS_S3_BUCKET")
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
        return {"path": path}
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 put error: {e}")
        raise HTTPException(500, f"Errore upload S3: {str(e)[:200]}")




def storage_get(path: str) -> tuple:
    s3 = get_s3()
    if not s3:
        raise HTTPException(500, "Storage S3 non disponibile")
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=path)
        data = obj["Body"].read()
        content_type = obj.get("ContentType", "application/octet-stream")
        return data, content_type
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 get error: {e}")
        raise HTTPException(500, f"Errore download S3: {str(e)[:200]}")

app = FastAPI(title="Gestionale Agenti di Commercio")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ----------------- Helpers -----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_id() -> str:
    return str(uuid.uuid4())


def clean(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


# ----------------- Models -----------------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str


class BonusTier(BaseModel):
    threshold: float   # fatturato minimo per ottenere il bonus
    bonus: float       # importo premio

class MandanteIn(BaseModel):
    name: str
    brand_color: Optional[str] = "#0A192F"
    commission_rate: float = 5.0
    notes: Optional[str] = ""
    target_monthly: Optional[float] = None
    target_yearly: Optional[float] = None
    target_clients: Optional[int] = None
    target_notes: Optional[str] = ""
    bonus_tiers: Optional[List[BonusTier]] = []


class ProductIn(BaseModel):
    mandante_id: str
    name: str
    sku: Optional[str] = ""
    price: float
    cost: Optional[float] = 0.0
    commission_rate: Optional[float] = None  # override mandante if set
    category: Optional[str] = ""


class ClientIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    vat_number: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    zone: Optional[str] = ""
    sector: Optional[str] = ""
    potential: Optional[str] = "medio"  # basso/medio/alto
    lat: Optional[float] = None
    lng: Optional[float] = None
    notes: Optional[str] = ""
    mandante_ids: List[str] = []


class LeadIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    source: Optional[str] = ""
    estimated_value: Optional[float] = 0.0
    status: str = "nuovo"  # nuovo, contattato, qualificato, trattativa, vinto, perso
    notes: Optional[str] = ""


class AppointmentIn(BaseModel):
    client_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    start: str  # ISO
    end: Optional[str] = None
    location: Optional[str] = ""
    status: str = "pianificato"  # pianificato, completato, annullato


class OfferLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float = 1
    unit_price: float = 0.0
    discount: float = 0.0


class OfferIn(BaseModel):
    client_id: str
    mandante_id: str
    title: str
    items: List[OfferLineItem] = []
    expires_at: Optional[str] = None
    status: str = "bozza"  # bozza, inviata, accettata, rifiutata, scaduta
    notes: Optional[str] = ""


class CommissionIn(BaseModel):
    offer_id: Optional[str] = None
    client_id: str
    mandante_id: str
    amount: float
    rate: float
    status: str = "maturato"  # maturato, incassato
    period: Optional[str] = None  # YYYY-MM


class DocumentIn(BaseModel):
    client_id: Optional[str] = None
    name: str
    category: str = "contratto"  # contratto, offerta, fattura, altro
    url: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[str] = []


class AutomationIn(BaseModel):
    name: str
    trigger: str  # offer_expiring, no_visit_30d, lead_inactive
    action: str  # send_reminder, create_task, send_email
    enabled: bool = True
    config: Dict[str, Any] = {}


class AIQuery(BaseModel):
    message: str
    context: Optional[str] = None


class SignatureIn(BaseModel):
    signature: str  # base64 PNG data URL
    signer_name: Optional[str] = ""


class EmailLogIn(BaseModel):
    to: str
    subject: str
    body: str
    client_id: Optional[str] = None
    offer_id: Optional[str] = None


# ----------------- Auth -----------------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email gia' registrata")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password troppo corta (min 6 caratteri)")
    user_id = gen_id()
    doc = {
        "id": user_id, "email": email, "name": payload.name,
        "password_hash": hash_password(payload.password),
        "role": "agent", "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    # Seed starter demo data so the new user lands on a populated app
    try:
        await seed_demo(user_id)
    except Exception as e:
        logger.warning(f"Seed for new user failed: {e}")
    token = create_access_token(user_id, email)
    response.set_cookie("access_token", token, httponly=True, secure=False,
                        samesite="lax", max_age=7*24*3600, path="/")
    out = clean(doc)
    out["token"] = token
    return out


@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = create_access_token(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, secure=False,
                        samesite="lax", max_age=7*24*3600, path="/")
    out = clean(user)
    out["token"] = token
    return out


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user


# ----------------- Mandanti -----------------
@api.get("/mandanti")
async def list_mandanti(user=Depends(get_current_user)):
    docs = await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    return docs


@api.post("/mandanti")
async def create_mandante(payload: MandanteIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(),
           "created_at": now_iso()}
    await db.mandanti.insert_one(doc)
    return clean(doc)


@api.put("/mandanti/{mid}")
async def update_mandante(mid: str, payload: MandanteIn, user=Depends(get_current_user)):
    res = await db.mandanti.update_one({"id": mid, "user_id": user["id"]},
                                       {"$set": payload.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Mandante non trovato")
    return {"ok": True}


@api.delete("/mandanti/{mid}")
async def delete_mandante(mid: str, user=Depends(get_current_user)):
    await db.mandanti.delete_one({"id": mid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Products -----------------
@api.get("/products")
async def list_products(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {"user_id": user["id"]}
    if mandante_id:
        q["mandante_id"] = mandante_id
    return await db.products.find(q, {"_id": 0}).to_list(1000)


@api.post("/products")
async def create_product(payload: ProductIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
    await db.products.insert_one(doc)
    return clean(doc)


@api.put("/products/{pid}")
async def update_product(pid: str, payload: ProductIn, user=Depends(get_current_user)):
    await db.products.update_one({"id": pid, "user_id": user["id"]}, {"$set": payload.model_dump()})
    return {"ok": True}


@api.delete("/products/{pid}")
async def delete_product(pid: str, user=Depends(get_current_user)):
    await db.products.delete_one({"id": pid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Clients -----------------
@api.get("/clients")
async def list_clients(zone: Optional[str] = None, sector: Optional[str] = None,
                       potential: Optional[str] = None, q: Optional[str] = None,
                       user=Depends(get_current_user)):
    query = {"user_id": user["id"]}
    if zone: query["zone"] = zone
    if sector: query["sector"] = sector
    if potential: query["potential"] = potential
    if q:
        query["$or"] = [
            {"company_name": {"$regex": q, "$options": "i"}},
            {"contact_name": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
        ]
    return await db.clients.find(query, {"_id": 0}).to_list(2000)


@api.post("/clients")
async def create_client(payload: ClientIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
    await db.clients.insert_one(doc)
    return clean(doc)


@api.get("/clients/{cid}")
async def get_client(cid: str, user=Depends(get_current_user)):
    c = await db.clients.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Cliente non trovato")
    offers = await db.offers.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
    appts = await db.appointments.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
    docs = await db.documents.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
    commissions = await db.commissions.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
    return {"client": c, "offers": offers, "appointments": appts, "documents": docs, "commissions": commissions}


@api.put("/clients/{cid}")
async def update_client(cid: str, payload: ClientIn, user=Depends(get_current_user)):
    res = await db.clients.update_one({"id": cid, "user_id": user["id"]}, {"$set": payload.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Cliente non trovato")
    return {"ok": True}


@api.delete("/clients/{cid}")
async def delete_client(cid: str, user=Depends(get_current_user)):
    await db.clients.delete_one({"id": cid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Leads -----------------
@api.get("/leads")
async def list_leads(user=Depends(get_current_user)):
    return await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)


@api.post("/leads")
async def create_lead(payload: LeadIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
    await db.leads.insert_one(doc)
    return clean(doc)


@api.put("/leads/{lid}")
async def update_lead(lid: str, payload: LeadIn, user=Depends(get_current_user)):
    await db.leads.update_one({"id": lid, "user_id": user["id"]}, {"$set": payload.model_dump()})
    return {"ok": True}


@api.patch("/leads/{lid}/status")
async def update_lead_status(lid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    await db.leads.update_one({"id": lid, "user_id": user["id"]}, {"$set": {"status": payload.get("status")}})
    return {"ok": True}


@api.delete("/leads/{lid}")
async def delete_lead(lid: str, user=Depends(get_current_user)):
    await db.leads.delete_one({"id": lid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Appointments -----------------
@api.get("/appointments")
async def list_appointments(user=Depends(get_current_user)):
    return await db.appointments.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)


@api.post("/appointments")
async def create_appointment(payload: AppointmentIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
    await db.appointments.insert_one(doc)
    return clean(doc)


@api.put("/appointments/{aid}")
async def update_appointment(aid: str, payload: AppointmentIn, user=Depends(get_current_user)):
    await db.appointments.update_one({"id": aid, "user_id": user["id"]}, {"$set": payload.model_dump()})
    return {"ok": True}


@api.delete("/appointments/{aid}")
async def delete_appointment(aid: str, user=Depends(get_current_user)):
    await db.appointments.delete_one({"id": aid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Offers -----------------
def calc_offer_total(items: List[dict]) -> float:
    total = 0.0
    for it in items:
        sub = it.get("quantity", 1) * it.get("unit_price", 0) * (1 - it.get("discount", 0)/100)
        total += sub
    return round(total, 2)


@api.get("/offers")
async def list_offers(user=Depends(get_current_user)):
    return await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)


@api.post("/offers")
async def create_offer(payload: OfferIn, user=Depends(get_current_user)):
    data = payload.model_dump()
    data["total"] = calc_offer_total(data["items"])
    doc = {"id": gen_id(), "user_id": user["id"], **data, "created_at": now_iso()}
    await db.offers.insert_one(doc)
    return clean(doc)


@api.put("/offers/{oid}")
async def update_offer(oid: str, payload: OfferIn, user=Depends(get_current_user)):
    data = payload.model_dump()
    data["total"] = calc_offer_total(data["items"])
    await db.offers.update_one({"id": oid, "user_id": user["id"]}, {"$set": data})
    return {"ok": True}


@api.patch("/offers/{oid}/status")
async def update_offer_status(oid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    new_status = payload.get("status")
    offer = await db.offers.find_one({"id": oid, "user_id": user["id"]}, {"_id": 0})
    if not offer:
        raise HTTPException(404, "Offerta non trovata")
    await db.offers.update_one({"id": oid, "user_id": user["id"]}, {"$set": {"status": new_status}})
    # If accepted, create commission record
    if new_status == "accettata" and offer.get("status") != "accettata":
        mandante = await db.mandanti.find_one({"id": offer["mandante_id"], "user_id": user["id"]}, {"_id": 0})
        rate = mandante.get("commission_rate", 5.0) if mandante else 5.0
        amount = offer.get("total", 0) * rate / 100
        comm = {
            "id": gen_id(), "user_id": user["id"], "offer_id": oid,
            "client_id": offer["client_id"], "mandante_id": offer["mandante_id"],
            "amount": round(amount, 2), "rate": rate, "status": "maturato",
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await db.commissions.insert_one(comm)
    return {"ok": True}


@api.delete("/offers/{oid}")
async def delete_offer(oid: str, user=Depends(get_current_user)):
    await db.offers.delete_one({"id": oid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Commissions -----------------
@api.get("/commissions")
async def list_commissions(user=Depends(get_current_user)):
    return await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)


@api.get("/commissions/bonus-summary")
async def bonus_summary(user=Depends(get_current_user)):
    """Calcola i bonus raggiunti per ogni mandante in base al fatturato delle provvigioni."""
    mandanti = await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)

    result = []
    for m in mandanti:
        tiers = m.get("bonus_tiers", [])
        if not tiers:
            continue
        # Somma fatturato (base_amount) o amount delle provvigioni di questo mandante
        fatturato = sum(
            c.get("base_amount", c.get("amount", 0) / (m.get("commission_rate", 5) / 100))
            for c in commissions if c.get("mandante_id") == m["id"]
        )
        # Ordina tiers per soglia crescente
        sorted_tiers = sorted(tiers, key=lambda t: t["threshold"])
        # Trova tutti i bonus raggiunti (tutti gli scaglioni superati)
        earned_tiers = [t for t in sorted_tiers if fatturato >= t["threshold"]]
        total_bonus = sum(t["bonus"] for t in earned_tiers)
        next_tier = next((t for t in sorted_tiers if fatturato < t["threshold"]), None)

        result.append({
            "mandante_id": m["id"],
            "mandante_name": m["name"],
            "brand_color": m.get("brand_color", "#0A192F"),
            "fatturato": round(fatturato, 2),
            "total_bonus": round(total_bonus, 2),
            "earned_tiers": earned_tiers,
            "next_tier": next_tier,
            "tiers": sorted_tiers,
        })
    return result


@api.patch("/commissions/{cid}/status")
async def update_commission_status(cid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    await db.commissions.update_one({"id": cid, "user_id": user["id"]},
                                    {"$set": {"status": payload.get("status")}})
    return {"ok": True}


@api.delete("/commissions/{cid}")
async def delete_commission(cid: str, user=Depends(get_current_user)):
    await db.commissions.delete_one({"id": cid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Documents -----------------
@api.get("/documents")
async def list_documents(user=Depends(get_current_user)):
    return await db.documents.find({"user_id": user["id"], "is_deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api.post("/documents")
async def create_document(payload: DocumentIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(),
           "is_deleted": False, "created_at": now_iso()}
    await db.documents.insert_one(doc)
    return clean(doc)


@api.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("altro"),
    client_id: Optional[str] = Form(None),
    notes: str = Form(""),
    tags: str = Form(""),
    user=Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(400, "File mancante")
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Estensione .{ext} non supportata. Consentite: PDF, Excel, Word, video, immagini.")
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File troppo grande (max {MAX_FILE_BYTES // (1024*1024)} MB)")
    if not data:
        raise HTTPException(400, "File vuoto")

    content_type = file.content_type or ALLOWED_EXT.get(ext, "application/octet-stream")
    storage_path = f"{APP_NAME}/uploads/{user['id']}/{gen_id()}.{ext}"

    try:
        result = storage_put(storage_path, data, content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, f"Errore caricamento: {str(e)[:200]}")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    doc = {
        "id": gen_id(), "user_id": user["id"],
        "client_id": client_id or None,
        "name": name or file.filename,
        "category": category,
        "url": "",
        "notes": notes,
        "tags": tag_list,
        "storage_path": result.get("path", storage_path),
        "original_filename": file.filename,
        "content_type": content_type,
        "size": len(data),
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.documents.insert_one(doc)
    return clean(doc)


@api.patch("/documents/{did}")
async def update_document_meta(did: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Update metadata (tags, name, category, notes, client_id) without re-uploading the file."""
    allowed = {k: v for k, v in payload.items() if k in {"name", "category", "notes", "client_id", "tags"}}
    if "tags" in allowed and isinstance(allowed["tags"], list):
        allowed["tags"] = [str(t).strip() for t in allowed["tags"] if str(t).strip()]
    res = await db.documents.update_one(
        {"id": did, "user_id": user["id"], "is_deleted": {"$ne": True}},
        {"$set": allowed},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Documento non trovato")
    return {"ok": True}


@api.get("/documents/{did}/download")
async def download_document(did: str, authorization: Optional[str] = Header(None), auth: Optional[str] = Query(None)):
    # Allow auth via Authorization header OR ?auth=token query param (for direct browser links)
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    doc = await db.documents.find_one({"id": did, "user_id": payload["sub"], "is_deleted": {"$ne": True}}, {"_id": 0})
    if not doc or not doc.get("storage_path"):
        raise HTTPException(404, "Documento non trovato")

    content, ctype = storage_get(doc["storage_path"])
    filename = doc.get("original_filename") or doc.get("name") or "file"
    return Response(
        content=content,
        media_type=doc.get("content_type") or ctype,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@api.delete("/documents/{did}")
async def delete_document(did: str, user=Depends(get_current_user)):
    # Soft delete (storage has no delete API)
    await db.documents.update_one(
        {"id": did, "user_id": user["id"]},
        {"$set": {"is_deleted": True}}
    )
    return {"ok": True}


# ----------------- Automations -----------------
@api.get("/automations")
async def list_automations(user=Depends(get_current_user)):
    return await db.automations.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)


@api.post("/automations")
async def create_automation(payload: AutomationIn, user=Depends(get_current_user)):
    doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
    await db.automations.insert_one(doc)
    return clean(doc)


@api.put("/automations/{aid}")
async def update_automation(aid: str, payload: AutomationIn, user=Depends(get_current_user)):
    await db.automations.update_one({"id": aid, "user_id": user["id"]}, {"$set": payload.model_dump()})
    return {"ok": True}


@api.delete("/automations/{aid}")
async def delete_automation(aid: str, user=Depends(get_current_user)):
    await db.automations.delete_one({"id": aid, "user_id": user["id"]})
    return {"ok": True}


# ----------------- Dashboard -----------------
@api.get("/dashboard/stats")
async def dashboard(user=Depends(get_current_user)):
    clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    appts = await db.appointments.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)

    revenue_won = sum(o.get("total", 0) for o in offers if o.get("status") == "accettata")
    revenue_pipeline = sum(o.get("total", 0) for o in offers if o.get("status") in ("inviata", "bozza"))
    accrued = sum(c.get("amount", 0) for c in commissions if c.get("status") == "maturato")
    collected = sum(c.get("amount", 0) for c in commissions if c.get("status") == "incassato")

    # Revenue by zone
    by_zone: Dict[str, float] = {}
    for o in offers:
        if o.get("status") != "accettata":
            continue
        cli = next((c for c in clients if c["id"] == o.get("client_id")), None)
        if cli:
            zone = cli.get("zone") or "N/D"
            by_zone[zone] = by_zone.get(zone, 0) + o.get("total", 0)

    # Monthly revenue (last 6 months) from accepted offers
    months: Dict[str, float] = {}
    for o in offers:
        if o.get("status") != "accettata":
            continue
        ca = o.get("created_at", "")
        if len(ca) >= 7:
            key = ca[:7]
            months[key] = months.get(key, 0) + o.get("total", 0)
    monthly = sorted([{"month": k, "revenue": round(v, 2)} for k, v in months.items()])[-6:]

    # Upcoming appointments (next 7 days)
    today = datetime.now(timezone.utc)
    week_later = today + timedelta(days=7)
    upcoming = []
    for a in appts:
        try:
            start = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
            if today <= start <= week_later and a.get("status") == "pianificato":
                upcoming.append(a)
        except Exception:
            pass

    # Goal: monthly target = 10000
    current_month_key = today.strftime("%Y-%m")
    current_month_rev = months.get(current_month_key, 0)
    goal = 10000

    return {
        "kpi": {
            "clients_count": len(clients),
            "leads_count": len(leads),
            "offers_count": len(offers),
            "revenue_won": round(revenue_won, 2),
            "revenue_pipeline": round(revenue_pipeline, 2),
            "commissions_accrued": round(accrued, 2),
            "commissions_collected": round(collected, 2),
            "current_month_revenue": round(current_month_rev, 2),
            "monthly_goal": goal,
            "goal_pct": round(min(100, (current_month_rev / goal) * 100) if goal else 0, 1),
        },
        "by_zone": [{"zone": k, "revenue": round(v, 2)} for k, v in by_zone.items()],
        "monthly": monthly,
        "upcoming_appointments": upcoming[:10],
        "pipeline": {
            "nuovo": sum(1 for l in leads if l.get("status") == "nuovo"),
            "contattato": sum(1 for l in leads if l.get("status") == "contattato"),
            "qualificato": sum(1 for l in leads if l.get("status") == "qualificato"),
            "trattativa": sum(1 for l in leads if l.get("status") == "trattativa"),
            "vinto": sum(1 for l in leads if l.get("status") == "vinto"),
            "perso": sum(1 for l in leads if l.get("status") == "perso"),
        },
    }


# ----------------- AI Assistant (Gemini 3 Flash) -----------------
async def gather_ai_context(user_id: str) -> str:
    clients = await db.clients.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    offers = await db.offers.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    appts = await db.appointments.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    commissions = await db.commissions.find({"user_id": user_id}, {"_id": 0}).to_list(200)

    # Clients with no recent visit
    today = datetime.now(timezone.utc)
    last_visit_map: Dict[str, datetime] = {}
    for a in appts:
        try:
            d = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
            cid = a.get("client_id")
            if cid and (cid not in last_visit_map or d > last_visit_map[cid]):
                last_visit_map[cid] = d
        except Exception:
            pass

    summary = []
    summary.append(f"Numero clienti: {len(clients)}, offerte: {len(offers)}, appuntamenti: {len(appts)}")
    summary.append("\nClienti (max 20):")
    for c in clients[:20]:
        last = last_visit_map.get(c["id"])
        days_ago = (today - last).days if last else "mai"
        summary.append(f"- {c['company_name']} ({c.get('zone','')}, potenziale {c.get('potential','medio')}) ultima visita: {days_ago}gg")
    summary.append("\nOfferte recenti:")
    for o in offers[-10:]:
        summary.append(f"- {o.get('title')} importo {o.get('total',0)}€ stato {o.get('status')}")
    return "\n".join(summary)


@api.post("/ai/chat")
async def ai_chat(payload: AIQuery, user=Depends(get_current_user)):
    import anthropic as anthropic_sdk
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY mancante")

    context = await gather_ai_context(user["id"])
    system = (
        "Sei un assistente commerciale italiano per agenti di commercio. "
        "Aiuti l'agente a decidere quali clienti visitare, analizzare le vendite, "
        "suggerire azioni concrete. Rispondi sempre in italiano, in modo conciso e pratico, "
        "con elenchi puntati quando possibile. Usa i dati forniti.\n\n"
        f"DATI ATTUALI:\n{context}"
    )

    try:
        client_ai = anthropic_sdk.Anthropic(api_key=api_key)
        message = client_ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": payload.message}],
        )
        response = message.content[0].text
    except Exception as e:
        logger.error(f"AI error: {e}")
        raise HTTPException(500, f"Errore AI: {str(e)[:200]}")

    log = {"id": gen_id(), "user_id": user["id"], "message": payload.message,
           "response": response, "created_at": now_iso()}
    await db.ai_logs.insert_one(log)
    return {"response": response}


@api.get("/ai/suggestions")
async def ai_suggestions(user=Depends(get_current_user)):
    import anthropic as anthropic_sdk
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"suggestions": []}
    context = await gather_ai_context(user["id"])
    system = (
        "Sei un consulente vendite italiano. Sulla base dei dati, suggerisci in italiano i 5 clienti "
        "più importanti da visitare questa settimana. Rispondi SOLO in JSON puro senza markdown, "
        "con questa struttura: {\"suggestions\":[{\"client\":\"nome\",\"reason\":\"motivo breve\",\"priority\":\"alta|media|bassa\"}]}"
    )
    try:
        client_ai = anthropic_sdk.Anthropic(api_key=api_key)
        message = client_ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": f"DATI:\n{context}\n\nSuggerisci 5 clienti da visitare."}],
        )
        response = message.content[0].text
        import json, re
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return data
    except Exception as e:
        logger.error(f"AI suggestions error: {e}")
    return {"suggestions": []}


# ----------------- Offer Signature -----------------
@api.post("/offers/{oid}/sign")
async def sign_offer(oid: str, payload: SignatureIn, user=Depends(get_current_user)):
    res = await db.offers.update_one(
        {"id": oid, "user_id": user["id"]},
        {"$set": {
            "signature": payload.signature,
            "signer_name": payload.signer_name,
            "signed_at": now_iso(),
            "status": "accettata",
        }}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Offerta non trovata")
    # Auto-create commission if needed
    offer = await db.offers.find_one({"id": oid, "user_id": user["id"]}, {"_id": 0})
    existing = await db.commissions.find_one({"offer_id": oid, "user_id": user["id"]})
    if not existing and offer:
        mandante = await db.mandanti.find_one({"id": offer["mandante_id"], "user_id": user["id"]}, {"_id": 0})
        rate = mandante.get("commission_rate", 5.0) if mandante else 5.0
        amount = offer.get("total", 0) * rate / 100
        comm = {
            "id": gen_id(), "user_id": user["id"], "offer_id": oid,
            "client_id": offer["client_id"], "mandante_id": offer["mandante_id"],
            "amount": round(amount, 2), "rate": rate, "status": "maturato",
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await db.commissions.insert_one(comm)
    return {"ok": True}


# ----------------- Email Mock -----------------
@api.post("/email/send")
async def send_email_mock(payload: EmailLogIn, user=Depends(get_current_user)):
    """MOCKED email sender - logs to db.email_logs only. No real delivery."""
    log = {
        "id": gen_id(), "user_id": user["id"],
        **payload.model_dump(),
        "status": "logged",
        "mocked": True,
        "created_at": now_iso(),
    }
    await db.email_logs.insert_one(log)
    logger.info(f"[MOCK EMAIL] To: {payload.to} | Subject: {payload.subject}")
    return {"ok": True, "mocked": True, "id": log["id"]}


@api.get("/email/logs")
async def list_email_logs(user=Depends(get_current_user)):
    return await db.email_logs.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


# ----------------- Export CSV -----------------
def csv_response(rows: List[dict], headers: List[str], filename: str):
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.DictWriter(buf, fieldnames=headers, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: r.get(h, "") for h in headers})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.get("/export/clients.csv")
async def export_clients(user=Depends(get_current_user)):
    clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    headers = ["company_name", "contact_name", "email", "phone", "vat_number",
               "address", "city", "province", "zone", "sector", "potential", "notes"]
    return csv_response(clients, headers, "clienti.csv")


@api.get("/export/offers.csv")
async def export_offers(user=Depends(get_current_user)):
    offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    clients = {c["id"]: c for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)}
    mandanti = {m["id"]: m for m in await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)}
    rows = []
    for o in offers:
        rows.append({
            "title": o.get("title"),
            "client": clients.get(o.get("client_id"), {}).get("company_name", ""),
            "mandante": mandanti.get(o.get("mandante_id"), {}).get("name", ""),
            "total": o.get("total", 0),
            "status": o.get("status"),
            "items_count": len(o.get("items", [])),
            "expires_at": (o.get("expires_at") or "")[:10],
            "created_at": (o.get("created_at") or "")[:10],
        })
    headers = ["title", "client", "mandante", "total", "status", "items_count", "expires_at", "created_at"]
    return csv_response(rows, headers, "offerte.csv")


@api.get("/export/commissions.csv")
async def export_commissions(user=Depends(get_current_user)):
    commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    clients = {c["id"]: c for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)}
    mandanti = {m["id"]: m for m in await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)}
    rows = []
    for c in commissions:
        rows.append({
            "period": c.get("period"),
            "client": clients.get(c.get("client_id"), {}).get("company_name", ""),
            "mandante": mandanti.get(c.get("mandante_id"), {}).get("name", ""),
            "amount": c.get("amount", 0),
            "rate": c.get("rate", 0),
            "status": c.get("status"),
        })
    headers = ["period", "client", "mandante", "amount", "rate", "status"]
    return csv_response(rows, headers, "provvigioni.csv")


@api.get("/export/leads.csv")
async def export_leads(user=Depends(get_current_user)):
    leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    headers = ["company_name", "contact_name", "email", "phone", "source",
               "estimated_value", "status", "notes", "created_at"]
    return csv_response(leads, headers, "lead.csv")


# ----------------- Seed Demo Data -----------------
async def seed_demo(user_id: str):
    if await db.mandanti.count_documents({"user_id": user_id}) > 0:
        return
    logger.info("Seeding demo data...")

    mandanti = [
        {"id": gen_id(), "user_id": user_id, "name": "Bellini Tessuti SRL", "brand_color": "#0A192F",
         "commission_rate": 8.0, "notes": "Tessuti pregiati Made in Italy", "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "name": "Caffè Aurora SpA", "brand_color": "#6B2C2C",
         "commission_rate": 5.5, "notes": "Torrefazione artigianale", "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "name": "Officine Meccaniche Po", "brand_color": "#1F4E3D",
         "commission_rate": 6.0, "notes": "Componenti industriali", "created_at": now_iso()},
    ]
    await db.mandanti.insert_many([dict(m) for m in mandanti])

    products = [
        {"id": gen_id(), "user_id": user_id, "mandante_id": mandanti[0]["id"], "name": "Velluto Sangallo 200gr", "sku": "VS-200", "price": 38.0, "cost": 18.0, "category": "Tessuti", "commission_rate": None, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "mandante_id": mandanti[0]["id"], "name": "Lino Premium 320gr", "sku": "LP-320", "price": 52.0, "cost": 22.0, "category": "Tessuti", "commission_rate": None, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "mandante_id": mandanti[1]["id"], "name": "Miscela Aurora 1kg", "sku": "AUR-1K", "price": 24.0, "cost": 9.0, "category": "Caffè", "commission_rate": None, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "mandante_id": mandanti[1]["id"], "name": "Capsule Espresso x100", "sku": "CAP-100", "price": 32.0, "cost": 14.0, "category": "Caffè", "commission_rate": 7.0, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "mandante_id": mandanti[2]["id"], "name": "Cuscinetto SKF 6205", "sku": "SKF-6205", "price": 18.5, "cost": 9.0, "category": "Meccanica", "commission_rate": None, "created_at": now_iso()},
    ]
    await db.products.insert_many([dict(p) for p in products])

    clients_seed = [
        ("Sartoria Conti Milano", "Marco Conti", "marco@sartoriaconti.it", "+39 02 1234567", "Via Brera 12", "Milano", "MI", "Lombardia", "Moda", "alto", 45.4719, 9.1881),
        ("Hotel Belvedere Como", "Laura Rossi", "info@hotelbelvedere.it", "+39 031 998877", "Via Lago 5", "Como", "CO", "Lombardia", "Hospitality", "alto", 45.8081, 9.0852),
        ("Bar Centrale Bergamo", "Giuseppe Verdi", "bar.centrale@gmail.com", "+39 035 223344", "Piazza Vecchia 8", "Bergamo", "BG", "Lombardia", "Ristorazione", "medio", 45.7036, 9.6695),
        ("Trattoria del Porto", "Anna Bianchi", "anna@trattoriaporto.it", "+39 010 556677", "Via del Porto 3", "Genova", "GE", "Liguria", "Ristorazione", "medio", 44.4056, 8.9463),
        ("Industria Romagnola SRL", "Luca Ferri", "amm@indromagnola.it", "+39 0544 887766", "Via Industriale 22", "Ravenna", "RA", "Emilia-Romagna", "Industria", "alto", 44.4184, 12.2035),
        ("Boutique Eleonora", "Eleonora Galli", "ele@boutique.it", "+39 055 111222", "Via Tornabuoni 9", "Firenze", "FI", "Toscana", "Moda", "medio", 43.7711, 11.2486),
        ("Pasticceria Aurora", "Roberto Esposito", "aurora@pasticceria.it", "+39 081 778899", "Via Toledo 44", "Napoli", "NA", "Campania", "Ristorazione", "basso", 40.8358, 14.2487),
        ("Officina Meccanica Po", "Davide Po", "davide@meccanicapo.it", "+39 011 445566", "Corso Francia 100", "Torino", "TO", "Piemonte", "Industria", "alto", 45.0703, 7.6869),
    ]
    clients = []
    for cn, contact, email, phone, addr, city, prov, zone, sector, pot, lat, lng in clients_seed:
        c = {
            "id": gen_id(), "user_id": user_id, "company_name": cn, "contact_name": contact,
            "email": email, "phone": phone, "vat_number": "", "address": addr, "city": city,
            "province": prov, "zone": zone, "sector": sector, "potential": pot,
            "lat": lat, "lng": lng, "notes": "",
            "mandante_ids": [mandanti[0]["id"]] if sector == "Moda" else
                            [mandanti[1]["id"]] if sector == "Ristorazione" else
                            [mandanti[2]["id"]] if sector == "Industria" else
                            [mandanti[1]["id"]],
            "created_at": now_iso(),
        }
        clients.append(c)
    await db.clients.insert_many([dict(c) for c in clients])

    leads = [
        ("Pizzeria Dante", "Mario Dante", "mario@pizzeriadante.it", "+39 06 555666", "passaparola", 4500, "nuovo"),
        ("Ristorante Il Faro", "Sara Costa", "sara@ilfaro.it", "+39 0586 332211", "fiera", 12000, "contattato"),
        ("Caffè Letterario", "Paolo Tosi", "info@caffeletterario.it", "+39 02 999888", "linkedin", 3200, "qualificato"),
        ("Hotel Tre Stelle", "Federico Greco", "fg@tre-stelle.it", "+39 045 776655", "referenza cliente", 18000, "trattativa"),
        ("Boutique Margot", "Margherita Rossi", "margot@boutique.it", "+39 011 332211", "instagram", 5500, "vinto"),
    ]
    lead_docs = [{"id": gen_id(), "user_id": user_id, "company_name": cn, "contact_name": ct, "email": em,
                  "phone": ph, "source": src, "estimated_value": v, "status": st, "notes": "",
                  "created_at": now_iso()} for cn, ct, em, ph, src, v, st in leads]
    await db.leads.insert_many([dict(l) for l in lead_docs])

    # Appointments: today + next 7 days
    base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    appt_data = [
        (clients[0], 0, "Presentazione collezione AI 2026", "Via Brera 12, Milano"),
        (clients[1], 1, "Riunione fornitura tessuti hotel", "Via Lago 5, Como"),
        (clients[2], 1, "Degustazione miscele caffè", "Piazza Vecchia 8, Bergamo"),
        (clients[3], 2, "Follow-up offerta capsule", "Via del Porto 3, Genova"),
        (clients[4], 3, "Sopralluogo tecnico cuscinetti", "Via Industriale 22, Ravenna"),
        (clients[5], 4, "Consegna campionario velluti", "Via Tornabuoni 9, Firenze"),
        (clients[7], 6, "Visita commerciale trimestrale", "Corso Francia 100, Torino"),
    ]
    appts = []
    for cli, day_offset, title, loc in appt_data:
        start = base + timedelta(days=day_offset, hours=(day_offset * 2) % 6)
        appts.append({
            "id": gen_id(), "user_id": user_id, "client_id": cli["id"], "title": title,
            "description": f"Incontro presso {cli['company_name']}",
            "start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat(),
            "location": loc, "status": "pianificato", "created_at": now_iso(),
        })
    await db.appointments.insert_many([dict(a) for a in appts])

    # Offers
    offers_data = [
        (clients[0], mandanti[0], "Fornitura velluti collezione P/E 2026", [
            {"product_id": products[0]["id"], "description": "Velluto Sangallo 200gr", "quantity": 50, "unit_price": 38.0, "discount": 5},
            {"product_id": products[1]["id"], "description": "Lino Premium 320gr", "quantity": 30, "unit_price": 52.0, "discount": 0},
        ], "accettata", -10),
        (clients[1], mandanti[1], "Fornitura caffè annuale Hotel Belvedere", [
            {"product_id": products[2]["id"], "description": "Miscela Aurora 1kg", "quantity": 200, "unit_price": 24.0, "discount": 8},
            {"product_id": products[3]["id"], "description": "Capsule Espresso x100", "quantity": 50, "unit_price": 32.0, "discount": 5},
        ], "inviata", -3),
        (clients[4], mandanti[2], "Fornitura cuscinetti industriali Q1", [
            {"product_id": products[4]["id"], "description": "Cuscinetto SKF 6205", "quantity": 500, "unit_price": 18.5, "discount": 10},
        ], "accettata", -25),
        (clients[3], mandanti[1], "Trattativa caffè ristorazione", [
            {"product_id": products[2]["id"], "description": "Miscela Aurora 1kg", "quantity": 80, "unit_price": 24.0, "discount": 5},
        ], "bozza", -1),
        (clients[5], mandanti[0], "Campionario velluti Boutique Eleonora", [
            {"product_id": products[0]["id"], "description": "Velluto Sangallo 200gr", "quantity": 25, "unit_price": 38.0, "discount": 0},
        ], "inviata", -7),
    ]
    offer_docs = []
    for cli, mand, title, items, status, days_offset in offers_data:
        total = calc_offer_total(items)
        created = (datetime.now(timezone.utc) + timedelta(days=days_offset)).isoformat()
        expires = (datetime.now(timezone.utc) + timedelta(days=days_offset + 30)).isoformat()
        offer_docs.append({
            "id": gen_id(), "user_id": user_id, "client_id": cli["id"], "mandante_id": mand["id"],
            "title": title, "items": items, "total": total, "expires_at": expires,
            "status": status, "notes": "", "created_at": created,
        })
    await db.offers.insert_many([dict(o) for o in offer_docs])

    # Commissions for accepted offers
    comm_docs = []
    for o in offer_docs:
        if o["status"] == "accettata":
            mand = next(m for m in mandanti if m["id"] == o["mandante_id"])
            amount = o["total"] * mand["commission_rate"] / 100
            comm_docs.append({
                "id": gen_id(), "user_id": user_id, "offer_id": o["id"],
                "client_id": o["client_id"], "mandante_id": o["mandante_id"],
                "amount": round(amount, 2), "rate": mand["commission_rate"],
                "status": "incassato" if "Q1" in o["title"] else "maturato",
                "period": o["created_at"][:7], "created_at": o["created_at"],
            })
    if comm_docs:
        await db.commissions.insert_many([dict(c) for c in comm_docs])

    # Documents
    docs = [
        (clients[0], "Contratto annuale Sartoria Conti", "contratto"),
        (clients[1], "Listino caffè 2026", "altro"),
        (clients[4], "Fattura fornitura cuscinetti Q1", "fattura"),
    ]
    doc_records = [{"id": gen_id(), "user_id": user_id, "client_id": cli["id"], "name": name,
                    "category": cat, "url": "", "notes": "", "created_at": now_iso()}
                   for cli, name, cat in docs]
    await db.documents.insert_many([dict(d) for d in doc_records])

    # Automations
    autos = [
        {"id": gen_id(), "user_id": user_id, "name": "Promemoria offerte in scadenza",
         "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
         "config": {"days_before": 3}, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "name": "Cliente non visitato da 30 giorni",
         "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
         "config": {}, "created_at": now_iso()},
        {"id": gen_id(), "user_id": user_id, "name": "Lead inattivo da 7 giorni",
         "trigger": "lead_inactive", "action": "send_email", "enabled": False,
         "config": {"days": 7}, "created_at": now_iso()},
    ]
    await db.automations.insert_many([dict(a) for a in autos])
    logger.info("Seed completed.")


# ----------------- Startup -----------------
@app.on_event("startup")
async def startup():
    # Init object storage (non-blocking on failure)
    try:
        if init_storage():
            logger.info("Object storage initialized")
        else:
            logger.warning("Object storage NOT initialized — uploads will fail")
    except Exception as e:
        logger.error(f"Storage init error: {e}")

    await db.users.create_index("email", unique=True)
    await db.clients.create_index([("user_id", 1)])
    await db.offers.create_index([("user_id", 1)])
    await db.documents.create_index([("user_id", 1), ("is_deleted", 1)])
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "agente@demo.it").lower()
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "demo1234")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        uid = gen_id()
        await db.users.insert_one({
            "id": uid, "email": admin_email, "name": "Mario Bianchi",
            "password_hash": hash_password(admin_pwd), "role": "agent",
            "created_at": now_iso(),
        })
        await seed_demo(uid)
    else:
        await seed_demo(existing["id"])


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ----------------- App wiring -----------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
