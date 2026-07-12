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
from core.database import db
from core.security import get_current_user, hash_password, verify_password, create_access_token
from core.utils import now_iso, gen_id, clean
from routers.clients import router as clients_router
from routers.leads import router as leads_router
from routers.appointments import router as appointments_router
from routers.mandanti import router as mandanti_router
from routers.products import router as products_router
from services.commission_service import calc_offer_total, get_commission_rate, check_and_award_bonus
from routers.offers import router as offers_router
from routers.commissions import router as commissions_router
from routers.documents import router as documents_router
from routers.automations import router as automations_router
from routers.dashboard import router as dashboard_router
from routers.export import router as export_router

# ----------------- Setup -----------------


JWT_SECRET = os.environ.get('JWT_SECRET', 'devsecret')

# Stripe & PayPal
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' o 'live'

PLANS = {
    'base': {'name': 'Base', 'price_eur': 6.00, 'stripe_price_id': os.environ.get('STRIPE_PRICE_BASE', ''), 'paypal_plan_id': os.environ.get('PAYPAL_PLAN_BASE', '')},
    'pro':  {'name': 'Pro',  'price_eur': 11.00, 'stripe_price_id': os.environ.get('STRIPE_PRICE_PRO', ''),  'paypal_plan_id': os.environ.get('PAYPAL_PLAN_PRO', '')},
}
JWT_ALG = 'HS256'

# Resend email
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "franco.bruni.art@gmail.com")
APP_FROM_EMAIL = os.environ.get("APP_FROM_EMAIL", "SALESFLY <noreply@salesfly.it>")

# Object Storage (AWS S3) — configurazione e funzioni centralizzate in services/storage_service.py
from services.storage_service import init_storage

async def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY non configurata — email non inviata")
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": APP_FROM_EMAIL,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email inviata a {to}: {subject}")
    except Exception as e:
        logger.error(f"Errore invio email a {to}: {e}")


app = FastAPI(title="Gestionale Agenti di Commercio")
api = APIRouter(prefix="/api")

from core.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

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
    plan: Optional[str] = "base"  # 'base' o 'pro'






class CommissionIn(BaseModel):
    offer_id: Optional[str] = None
    client_id: str
    mandante_id: str
    amount: float
    rate: float
    status: str = "maturato"  # maturato, incassato
    period: Optional[str] = None  # YYYY-MM


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
    plan = payload.plan if payload.plan in PLANS else "base"
    doc = {
        "id": user_id, "email": email, "name": payload.name,
        "password_hash": hash_password(payload.password),
        "role": "agent", "created_at": now_iso(),
        "plan": plan,
        "subscription_status": "trial",  # trial | active | cancelled | expired
        "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "paypal_subscription_id": None,
    }
    await db.users.insert_one(doc)
    # Seed starter demo data so the new user lands on a populated app
    try:
        await seed_demo(user_id)
    except Exception as e:
        logger.warning(f"Seed for new user failed: {e}")
    token = create_access_token(user_id, email)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                        samesite="none", max_age=7*24*3600, path="/")

    # Email benvenuto all'utente (non bloccante)
    try:
      await send_email(
        to=email,
        subject="Benvenuto su SALESFLY — il tuo gestionale è pronto!",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;background:#F9F9F8;">
          <div style="background:#0A192F;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
            <span style="color:#FF5A00;font-weight:900;font-size:22px;letter-spacing:2px;">SALESFLY.</span>
          </div>
          <h2 style="color:#0A192F;margin:0 0 12px;">Benvenuto, {doc.get('name', '')}!</h2>
          <p style="color:#52525B;font-size:15px;line-height:1.6;">
            Il tuo account è stato creato con successo. Hai <strong>14 giorni di prova gratuita</strong> 
            per esplorare tutte le funzionalità di SALESFLY.
          </p>
          <div style="background:#fff;border:1px solid #E4E4E1;border-radius:8px;padding:20px;margin:24px 0;">
            <div style="font-size:12px;color:#A1A1AA;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Piano attivo</div>
            <div style="font-size:20px;font-weight:900;color:#FF5A00;">{plan.upper()} — €{PLANS[plan]['price_eur']:.0f}/mese</div>
            <div style="font-size:13px;color:#52525B;margin-top:4px;">14 giorni gratuiti, nessuna carta richiesta</div>
          </div>
          <a href="https://salesfly.netlify.app" 
             style="display:inline-block;background:#0A192F;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
            Accedi al gestionale →
          </a>
          <p style="color:#A1A1AA;font-size:12px;margin-top:32px;">
            SALESFLY — Gestionale per agenti di commercio<br>
            Se non hai creato questo account, ignora questa email.
          </p>
        </div>
        """
      )
    except Exception as mail_err:
        logger.warning(f"Email benvenuto non inviata: {mail_err}")

    # Email notifica admin (non bloccante)
    try:
      await send_email(
        to=ADMIN_NOTIFY_EMAIL,
        subject=f"🆕 Nuovo utente registrato: {email}",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;">
          <h2 style="color:#0A192F;">Nuovo utente registrato</h2>
          <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <tr><td style="padding:8px;color:#52525B;width:120px;">Nome</td><td style="padding:8px;font-weight:600;">{doc.get('name','')}</td></tr>
            <tr style="background:#F9F9F8;"><td style="padding:8px;color:#52525B;">Email</td><td style="padding:8px;font-weight:600;">{email}</td></tr>
            <tr><td style="padding:8px;color:#52525B;">Piano</td><td style="padding:8px;font-weight:600;color:#FF5A00;">{plan.upper()}</td></tr>
            <tr style="background:#F9F9F8;"><td style="padding:8px;color:#52525B;">Data</td><td style="padding:8px;">{now_iso()[:16].replace('T',' ')}</td></tr>
          </table>
          <a href="https://salesfly.netlify.app/admin"
             style="display:inline-block;margin-top:20px;background:#FF5A00;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
            Vedi Admin Dashboard →
          </a>
        </div>
        """
      )
    except Exception as mail_err:
        logger.warning(f"Email admin non inviata: {mail_err}")

    out = clean(doc)
    
    return out


@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = create_access_token(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                        samesite="none", max_age=7*24*3600, path="/")
    out = clean(user)
    
    return out


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user


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


@api.get("/ai/history")
async def ai_history(user=Depends(get_current_user)):
    """Restituisce gli ultimi 30 messaggi della cronologia AI."""
    logs = await db.ai_logs.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(30)
    return logs


@api.delete("/ai/history")
async def clear_ai_history(user=Depends(get_current_user)):
    """Cancella tutta la cronologia AI dell'utente."""
    await db.ai_logs.delete_many({"user_id": user["id"]})
    return {"ok": True}


# Definizione tools CRM per l'AI
CRM_TOOLS = [
    {
        "name": "add_client",
        "description": "Aggiunge un nuovo cliente al CRM. Usare quando l'utente chiede di aggiungere/creare un cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Nome azienda o cliente"},
                "contact_name": {"type": "string", "description": "Nome del referente"},
                "email": {"type": "string", "description": "Email"},
                "phone": {"type": "string", "description": "Telefono"},
                "city": {"type": "string", "description": "Città"},
                "notes": {"type": "string", "description": "Note aggiuntive"},
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "add_appointment",
        "description": "Aggiunge un nuovo appuntamento in agenda. Usare quando l'utente chiede di aggiungere/fissare un appuntamento o una visita.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titolo appuntamento"},
                "start": {"type": "string", "description": "Data e ora ISO8601, es: 2026-05-15T10:00:00"},
                "client_name": {"type": "string", "description": "Nome cliente (per trovarlo nel CRM)"},
                "location": {"type": "string", "description": "Luogo"},
                "description": {"type": "string", "description": "Note"},
            },
            "required": ["title", "start"]
        }
    },
    {
        "name": "add_lead",
        "description": "Aggiunge un nuovo lead/prospect alla pipeline. Usare quando l'utente chiede di aggiungere un lead o un prospect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Nome azienda"},
                "contact_name": {"type": "string", "description": "Nome referente"},
                "email": {"type": "string", "description": "Email"},
                "phone": {"type": "string", "description": "Telefono"},
                "value": {"type": "number", "description": "Valore stimato opportunità"},
                "notes": {"type": "string", "description": "Note"},
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "add_note_to_client",
        "description": "Aggiunge una nota a un cliente esistente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Nome del cliente"},
                "note": {"type": "string", "description": "Testo della nota da aggiungere"},
            },
            "required": ["client_name", "note"]
        }
    },
    {
        "name": "add_offer",
        "description": "Registra una vendita/offerta per un cliente e un mandante. Usare quando l'utente chiede di registrare una vendita, un ordine o un'offerta. Se l'utente dice che la vendita è già conclusa/confermata, imposta accepted a true: in quel caso viene generata automaticamente anche la provvigione, secondo l'aliquota del mandante (che può differire tra vendite nuove e rinnovi).",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Nome del cliente (per trovarlo nel CRM)"},
                "mandante_name": {"type": "string", "description": "Nome del mandante (per trovarlo nel CRM)"},
                "title": {"type": "string", "description": "Titolo/oggetto della vendita, es: 'Fornitura materiali maggio'"},
                "product_names": {"type": "array", "items": {"type": "string"}, "description": "Nomi dei prodotti venduti, se noti"},
                "quantities": {"type": "array", "items": {"type": "number"}, "description": "Quantità per ciascun prodotto, stesso ordine di product_names"},
                "unit_prices": {"type": "array", "items": {"type": "number"}, "description": "Prezzo unitario per ciascun prodotto; se omesso viene usato il prezzo di listino del prodotto"},
                "total_amount": {"type": "number", "description": "Importo totale della vendita, da usare solo se non si conoscono i singoli prodotti/prezzi"},
                "accepted": {"type": "boolean", "description": "True se la vendita è già confermata/conclusa (genera anche la provvigione), false se è solo un preventivo/bozza"},
                "sale_type": {"type": "string", "enum": ["nuovo", "rinnovo"], "description": "Tipo di vendita: 'nuovo' per un nuovo cliente/contratto, 'rinnovo' per il rinnovo di uno esistente. Determina quale aliquota di provvigione del mandante viene applicata. Default 'nuovo' se non specificato."},
            },
            "required": ["client_name", "mandante_name"]
        }
    },
]


async def execute_crm_tool(tool_name: str, tool_input: dict, user_id: str) -> str:
    """Esegue un tool CRM e restituisce il risultato come stringa."""
    try:
        if tool_name == "add_client":
            doc = {
                "id": gen_id(), "user_id": user_id,
                "company_name": tool_input.get("company_name", ""),
                "contact_name": tool_input.get("contact_name", ""),
                "email": tool_input.get("email", ""),
                "phone": tool_input.get("phone", ""),
                "city": tool_input.get("city", ""),
                "address": tool_input.get("address", ""),
                "province": tool_input.get("province", ""),
                "zone": tool_input.get("zone", ""),
                "sector": tool_input.get("sector", ""),
                "vat_number": tool_input.get("vat_number", ""),
                "potential": tool_input.get("potential", "medio"),
                "notes": tool_input.get("notes", ""),
                "mandante_ids": [],
                "lat": None, "lng": None,
                "segment": "prospect", "status": "attivo",
                "created_at": now_iso(),
            }
            await db.clients.insert_one(doc)
            return f"✅ Cliente '{doc['company_name']}' aggiunto con successo al CRM."

        elif tool_name == "add_appointment":
            # Cerca cliente per nome se specificato
            client_id = ""
            client_name = tool_input.get("client_name", "")
            if client_name:
                cli = await db.clients.find_one(
                    {"user_id": user_id, "company_name": {"$regex": client_name, "$options": "i"}},
                    {"_id": 0}
                )
                if cli:
                    client_id = cli["id"]

            doc = {
                "id": gen_id(), "user_id": user_id,
                "title": tool_input.get("title", ""),
                "start": tool_input.get("start", ""),
                "client_id": client_id,
                "location": tool_input.get("location", ""),
                "description": tool_input.get("description", ""),
                "status": "pianificato",
                "created_at": now_iso(),
            }
            await db.appointments.insert_one(doc)
            return f"✅ Appuntamento '{doc['title']}' fissato per {doc['start'][:10]} alle {doc['start'][11:16]}."

        elif tool_name == "add_lead":
            doc = {
                "id": gen_id(), "user_id": user_id,
                "company_name": tool_input.get("company_name", ""),
                "contact_name": tool_input.get("contact_name", ""),
                "email": tool_input.get("email", ""),
                "phone": tool_input.get("phone", ""),
                "value": tool_input.get("value", 0),
                "notes": tool_input.get("notes", ""),
                "stage": "nuovo", "status": "aperto",
                "created_at": now_iso(),
            }
            await db.leads.insert_one(doc)
            return f"✅ Lead '{doc['company_name']}' aggiunto alla pipeline."

        elif tool_name == "add_note_to_client":
            client_name = tool_input.get("client_name", "")
            note = tool_input.get("note", "")
            cli = await db.clients.find_one(
                {"user_id": user_id, "company_name": {"$regex": client_name, "$options": "i"}},
                {"_id": 0}
            )
            if not cli:
                return f"❌ Cliente '{client_name}' non trovato nel CRM."
            existing_notes = cli.get("notes", "")
            new_notes = f"{existing_notes}\n[{now_iso()[:10]}] {note}".strip()
            await db.clients.update_one({"id": cli["id"]}, {"$set": {"notes": new_notes}})
            return f"✅ Nota aggiunta al cliente '{cli['company_name']}'."

        elif tool_name == "add_offer":
            client_name = tool_input.get("client_name", "")
            mandante_name = tool_input.get("mandante_name", "")

            cli = await db.clients.find_one(
                {"user_id": user_id, "company_name": {"$regex": client_name, "$options": "i"}},
                {"_id": 0}
            )
            if not cli:
                return f"❌ Cliente '{client_name}' non trovato nel CRM."

            mand = await db.mandanti.find_one(
                {"user_id": user_id, "name": {"$regex": mandante_name, "$options": "i"}},
                {"_id": 0}
            )
            if not mand:
                return f"❌ Mandante '{mandante_name}' non trovato nel CRM."

            product_names = tool_input.get("product_names") or []
            quantities = tool_input.get("quantities") or []
            unit_prices = tool_input.get("unit_prices") or []

            items = []
            if product_names:
                for i, pname in enumerate(product_names):
                    prod = await db.products.find_one(
                        {"user_id": user_id, "mandante_id": mand["id"], "name": {"$regex": pname, "$options": "i"}},
                        {"_id": 0}
                    )
                    qty = quantities[i] if i < len(quantities) else 1
                    price = unit_prices[i] if i < len(unit_prices) else (prod.get("price", 0) if prod else 0)
                    items.append({
                        "product_id": prod["id"] if prod else None,
                        "description": prod["name"] if prod else pname,
                        "quantity": qty, "unit_price": price, "discount": 0,
                    })
            else:
                total_amount = tool_input.get("total_amount", 0)
                items.append({
                    "product_id": None,
                    "description": tool_input.get("title", "Vendita"),
                    "quantity": 1, "unit_price": total_amount, "discount": 0,
                })

            total = calc_offer_total(items)
            accepted = bool(tool_input.get("accepted", False))
            status = "accettata" if accepted else "bozza"
            sale_type = tool_input.get("sale_type", "nuovo")
            if sale_type not in ("nuovo", "rinnovo"):
                sale_type = "nuovo"

            offer_doc = {
                "id": gen_id(), "user_id": user_id,
                "client_id": cli["id"], "mandante_id": mand["id"],
                "title": tool_input.get("title") or f"Vendita {cli['company_name']}",
                "items": items, "total": total,
                "expires_at": None, "status": status, "sale_type": sale_type, "notes": "",
                "created_at": now_iso(),
            }
            await db.offers.insert_one(offer_doc)

            msg = f"✅ Vendita registrata: {cli['company_name']} - {mand['name']} - €{total:.2f} ({sale_type}), stato: {status}."

            if accepted:
                rate = get_commission_rate(mand, sale_type)
                amount = round(total * rate / 100, 2)
                comm = {
                    "id": gen_id(), "user_id": user_id, "offer_id": offer_doc["id"],
                    "client_id": cli["id"], "mandante_id": mand["id"],
                    "amount": amount, "rate": rate, "base_amount": total,
                    "sale_type": sale_type, "status": "maturato",
                    "period": datetime.now(timezone.utc).strftime("%Y-%m"),
                    "created_at": now_iso(),
                }
                await db.commissions.insert_one(comm)
                await check_and_award_bonus(user_id, mand["id"])
                msg += f" Provvigione generata: €{amount:.2f} ({rate}%)."

            return msg

        return f"❌ Tool '{tool_name}' non riconosciuto."
    except Exception as e:
        logger.error(f"CRM tool error: {e}")
        return f"❌ Errore durante l'operazione: {str(e)[:200]}"


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
        "suggerire azioni concrete. Puoi anche modificare il CRM: aggiungere clienti, "
        "appuntamenti, lead, note e vendite/offerte. Quando l'utente ti chiede di fare "
        "un'azione sul CRM, usa i tool disponibili. Se l'utente chiede informazioni "
        "aggiornate o esterne al CRM (es. un'azienda, un prezzo, una notizia recente), "
        "usa la ricerca web. Rispondi sempre in italiano, in modo conciso e pratico, "
        "con elenchi puntati quando possibile. Usa i dati forniti.\n\n"
        f"DATI ATTUALI:\n{context}"
    )

    # Carica ultimi 10 scambi
    history = await db.ai_logs.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(10)
    history.reverse()

    messages = []
    for h in history:
        messages.append({"role": "user", "content": h["message"]})
        messages.append({"role": "assistant", "content": h["response"]})
    messages.append({"role": "user", "content": payload.message})

    try:
        client_ai = anthropic_sdk.Anthropic(api_key=api_key)
        actions_performed = []

        # Primo turno — potrebbe usare tool
        message = client_ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            tools=CRM_TOOLS + [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=messages,
        )

        # Gestisci tool use in loop
        while message.stop_reason == "tool_use":
            tool_results = []
            for block in message.content:
                if block.type == "tool_use":
                    result = await execute_crm_tool(block.name, block.input, user["id"])
                    actions_performed.append(result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Continua la conversazione con i risultati dei tool
            messages_with_tools = messages + [
                {"role": "assistant", "content": message.content},
                {"role": "user", "content": tool_results},
            ]
            message = client_ai.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system,
                tools=CRM_TOOLS + [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
                messages=messages_with_tools,
            )

        # Estrai risposta testuale finale
        response = " ".join(
            block.text for block in message.content if hasattr(block, "text")
        )

    except Exception as e:
        logger.error(f"AI error: {e}")
        raise HTTPException(500, f"Errore AI: {str(e)[:200]}")

    log = {"id": gen_id(), "user_id": user["id"], "message": payload.message,
           "response": response, "created_at": now_iso()}
    await db.ai_logs.insert_one(log)
    return {"response": response, "actions": actions_performed}


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
        await check_and_award_bonus(user["id"], offer["mandante_id"])
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


# ----------------- Admin Setup -----------------

@api.post("/auth/make-admin")
async def make_admin(payload: dict = Body(...)):
    """Route temporanea per promuovere un utente ad admin. Richiede ADMIN_SECRET."""
    secret = os.environ.get("ADMIN_SECRET", "")
    if not secret or payload.get("secret") != secret:
        raise HTTPException(403, "Secret non valido")
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Email mancante")
    res = await db.users.update_one({"email": email}, {"$set": {"role": "admin"}})
    if res.matched_count == 0:
        raise HTTPException(404, f"Utente {email} non trovato")
    return {"ok": True, "message": f"{email} è ora admin"}


# ----------------- Subscription & Payments -----------------

def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"

def require_admin(user=Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(403, "Accesso riservato agli amministratori")
    return user

def subscription_active(user: dict) -> bool:
    status = user.get("subscription_status", "trial")
    if status == "active":
        return True
    if status == "trial":
        trial_end = user.get("trial_ends_at", "")
        try:
            from datetime import datetime, timezone
            end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < end
        except Exception:
            return True
    return False


@api.get("/subscription/plans")
async def get_plans():
    return [{"id": k, **v} for k, v in PLANS.items()]


@api.get("/subscription/status")
async def subscription_status(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return {
        "plan": u.get("plan", "base"),
        "status": u.get("subscription_status", "trial"),
        "trial_ends_at": u.get("trial_ends_at"),
        "active": subscription_active(u),
    }


@api.post("/subscription/create-stripe-session")
async def create_stripe_session(payload: dict = Body(...), user=Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe non configurato")
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        plan_id = payload.get("plan", "base")
        plan = PLANS.get(plan_id)
        if not plan:
            raise HTTPException(400, "Piano non valido")

        # Crea o recupera customer Stripe
        u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        customer_id = u.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"], name=u.get("name", ""))
            customer_id = customer.id
            await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer_id}})

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            success_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?success=stripe",
            cancel_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?cancelled=1",
            metadata={"user_id": user["id"], "plan": plan_id},
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe session error: {e}")
        raise HTTPException(500, str(e)[:200])


@api.post("/subscription/stripe-webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe non configurato")
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, str(e))

    if event["type"] == "checkout.session.completed":
        meta = event["data"]["object"].get("metadata", {})
        user_id = meta.get("user_id")
        plan = meta.get("plan", "base")
        sub_id = event["data"]["object"].get("subscription")
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": {
                "plan": plan,
                "subscription_status": "active",
                "stripe_subscription_id": sub_id,
            }})
    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub = event["data"]["object"]
        await db.users.update_one(
            {"stripe_subscription_id": sub["id"]},
            {"$set": {"subscription_status": "cancelled"}}
        )
    return {"ok": True}


@api.post("/subscription/paypal-capture")
async def paypal_capture(payload: dict = Body(...), user=Depends(get_current_user)):
    """Conferma abbonamento PayPal dopo approvazione."""
    subscription_id = payload.get("subscription_id")
    plan_id = payload.get("plan", "base")
    if not subscription_id:
        raise HTTPException(400, "subscription_id mancante")
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "plan": plan_id,
        "subscription_status": "active",
        "paypal_subscription_id": subscription_id,
    }})
    return {"ok": True}


@api.post("/subscription/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    # Cancella su Stripe se presente
    if u.get("stripe_subscription_id") and STRIPE_SECRET_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            stripe.Subscription.cancel(u["stripe_subscription_id"])
        except Exception as e:
            logger.warning(f"Stripe cancel error: {e}")
    await db.users.update_one({"id": user["id"]}, {"$set": {"subscription_status": "cancelled"}})
    return {"ok": True}


# ----------------- Admin Dashboard -----------------

@api.get("/admin/stats")
async def admin_stats(admin=Depends(require_admin)):
    total = await db.users.count_documents({"role": "agent"})
    active = await db.users.count_documents({"role": "agent", "subscription_status": "active"})
    trial = await db.users.count_documents({"role": "agent", "subscription_status": "trial"})
    cancelled = await db.users.count_documents({"role": "agent", "subscription_status": "cancelled"})
    base = await db.users.count_documents({"role": "agent", "plan": "base", "subscription_status": "active"})
    pro = await db.users.count_documents({"role": "agent", "plan": "pro", "subscription_status": "active"})
    mrr = (base * PLANS["base"]["price_eur"]) + (pro * PLANS["pro"]["price_eur"])
    return {
        "total_users": total,
        "active": active,
        "trial": trial,
        "cancelled": cancelled,
        "plan_base": base,
        "plan_pro": pro,
        "mrr": round(mrr, 2),
        "arr": round(mrr * 12, 2),
    }


@api.get("/admin/users")
async def admin_users(admin=Depends(require_admin), page: int = 1, limit: int = 50):
    skip = (page - 1) * limit
    users = await db.users.find(
        {"role": "agent"},
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).skip(skip).to_list(limit)
    total = await db.users.count_documents({"role": "agent"})
    return {"users": users, "total": total, "page": page}


@api.patch("/admin/users/{uid}")
async def admin_update_user(uid: str, payload: dict = Body(...), admin=Depends(require_admin)):
    allowed = {"plan", "subscription_status", "role"}
    update = {k: v for k, v in payload.items() if k in allowed}
    if not update:
        raise HTTPException(400, "Nessun campo valido")
    await db.users.update_one({"id": uid}, {"$set": update})
    return {"ok": True}


@api.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, admin=Depends(require_admin)):
    await db.users.delete_one({"id": uid})
    return {"ok": True}


# ----------------- App wiring -----------------
app.include_router(api)
app.include_router(clients_router)
app.include_router(leads_router)
app.include_router(appointments_router)
app.include_router(mandanti_router)
app.include_router(products_router)
app.include_router(offers_router)
app.include_router(commissions_router)
app.include_router(documents_router)
app.include_router(automations_router)
app.include_router(dashboard_router)
app.include_router(export_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://salesfly.it", "https://www.salesfly.it", "https://main--salesfly.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
