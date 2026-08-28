import logging
from datetime import datetime, timedelta, timezone

from core.utils import gen_id, now_iso
from repositories.appointment_repository import appointment_repository
from repositories.automation_repository import automation_repository
from repositories.client_repository import client_repository
from repositories.commission_repository import commission_repository
from repositories.document_repository import document_repository
from repositories.lead_repository import lead_repository
from repositories.mandante_repository import mandante_repository
from repositories.offer_repository import offer_repository
from repositories.product_repository import product_repository
from services.commission_service import calc_offer_total

logger = logging.getLogger(__name__)


class SeedService:
    def __init__(
        self,
        mandante_repo=mandante_repository,
        product_repo=product_repository,
        client_repo=client_repository,
        lead_repo=lead_repository,
        appointment_repo=appointment_repository,
        offer_repo=offer_repository,
        commission_repo=commission_repository,
        document_repo=document_repository,
        automation_repo=automation_repository,
    ):
        self.mandante_repo = mandante_repo
        self.product_repo = product_repo
        self.client_repo = client_repo
        self.lead_repo = lead_repo
        self.appointment_repo = appointment_repo
        self.offer_repo = offer_repo
        self.commission_repo = commission_repo
        self.document_repo = document_repo
        self.automation_repo = automation_repo

    async def seed_demo(self, user_id: str) -> None:
        if await self.mandante_repo.count(user_id) > 0:
            return
        logger.info("Seeding demo data...")

        mandanti = [
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Bellini Tessuti SRL",
                "brand_color": "#0A192F",
                "commission_rate": 8.0,
                "notes": "Tessuti pregiati Made in Italy",
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Caffè Aurora SpA",
                "brand_color": "#6B2C2C",
                "commission_rate": 5.5,
                "notes": "Torrefazione artigianale",
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Officine Meccaniche Po",
                "brand_color": "#1F4E3D",
                "commission_rate": 6.0,
                "notes": "Componenti industriali",
                "created_at": now_iso(),
            },
        ]
        await self.mandante_repo.insert_many([dict(m) for m in mandanti])

        products = [
            {
                "id": gen_id(),
                "user_id": user_id,
                "mandante_id": mandanti[0]["id"],
                "name": "Velluto Sangallo 200gr",
                "sku": "VS-200",
                "price": 38.0,
                "cost": 18.0,
                "category": "Tessuti",
                "commission_rate": None,
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "mandante_id": mandanti[0]["id"],
                "name": "Lino Premium 320gr",
                "sku": "LP-320",
                "price": 52.0,
                "cost": 22.0,
                "category": "Tessuti",
                "commission_rate": None,
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "mandante_id": mandanti[1]["id"],
                "name": "Miscela Aurora 1kg",
                "sku": "AUR-1K",
                "price": 24.0,
                "cost": 9.0,
                "category": "Caffè",
                "commission_rate": None,
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "mandante_id": mandanti[1]["id"],
                "name": "Capsule Espresso x100",
                "sku": "CAP-100",
                "price": 32.0,
                "cost": 14.0,
                "category": "Caffè",
                "commission_rate": 7.0,
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "mandante_id": mandanti[2]["id"],
                "name": "Cuscinetto SKF 6205",
                "sku": "SKF-6205",
                "price": 18.5,
                "cost": 9.0,
                "category": "Meccanica",
                "commission_rate": None,
                "created_at": now_iso(),
            },
        ]
        await self.product_repo.insert_many([dict(p) for p in products])

        clients_seed = [
            (
                "Sartoria Conti Milano",
                "Marco Conti",
                "marco@sartoriaconti.it",
                "+39 02 1234567",
                "Via Brera 12",
                "Milano",
                "MI",
                "Lombardia",
                "Moda",
                "alto",
                45.4719,
                9.1881,
            ),
            (
                "Hotel Belvedere Como",
                "Laura Rossi",
                "info@hotelbelvedere.it",
                "+39 031 998877",
                "Via Lago 5",
                "Como",
                "CO",
                "Lombardia",
                "Hospitality",
                "alto",
                45.8081,
                9.0852,
            ),
            (
                "Bar Centrale Bergamo",
                "Giuseppe Verdi",
                "bar.centrale@gmail.com",
                "+39 035 223344",
                "Piazza Vecchia 8",
                "Bergamo",
                "BG",
                "Lombardia",
                "Ristorazione",
                "medio",
                45.7036,
                9.6695,
            ),
            (
                "Trattoria del Porto",
                "Anna Bianchi",
                "anna@trattoriaporto.it",
                "+39 010 556677",
                "Via del Porto 3",
                "Genova",
                "GE",
                "Liguria",
                "Ristorazione",
                "medio",
                44.4056,
                8.9463,
            ),
            (
                "Industria Romagnola SRL",
                "Luca Ferri",
                "amm@indromagnola.it",
                "+39 0544 887766",
                "Via Industriale 22",
                "Ravenna",
                "RA",
                "Emilia-Romagna",
                "Industria",
                "alto",
                44.4184,
                12.2035,
            ),
            (
                "Boutique Eleonora",
                "Eleonora Galli",
                "ele@boutique.it",
                "+39 055 111222",
                "Via Tornabuoni 9",
                "Firenze",
                "FI",
                "Toscana",
                "Moda",
                "medio",
                43.7711,
                11.2486,
            ),
            (
                "Pasticceria Aurora",
                "Roberto Esposito",
                "aurora@pasticceria.it",
                "+39 081 778899",
                "Via Toledo 44",
                "Napoli",
                "NA",
                "Campania",
                "Ristorazione",
                "basso",
                40.8358,
                14.2487,
            ),
            (
                "Officina Meccanica Po",
                "Davide Po",
                "davide@meccanicapo.it",
                "+39 011 445566",
                "Corso Francia 100",
                "Torino",
                "TO",
                "Piemonte",
                "Industria",
                "alto",
                45.0703,
                7.6869,
            ),
        ]
        clients = []
        for (
            cn,
            contact,
            email,
            phone,
            addr,
            city,
            prov,
            zone,
            sector,
            pot,
            lat,
            lng,
        ) in clients_seed:
            c = {
                "id": gen_id(),
                "user_id": user_id,
                "company_name": cn,
                "contact_name": contact,
                "email": email,
                "phone": phone,
                "vat_number": "",
                "address": addr,
                "city": city,
                "province": prov,
                "zone": zone,
                "sector": sector,
                "potential": pot,
                "lat": lat,
                "lng": lng,
                "notes": "",
                "mandante_ids": (
                    [mandanti[0]["id"]]
                    if sector == "Moda"
                    else (
                        [mandanti[1]["id"]]
                        if sector == "Ristorazione"
                        else (
                            [mandanti[2]["id"]]
                            if sector == "Industria"
                            else [mandanti[1]["id"]]
                        )
                    )
                ),
                "created_at": now_iso(),
            }
            clients.append(c)
        await self.client_repo.insert_many([dict(c) for c in clients])

        leads = [
            (
                "Pizzeria Dante",
                "Mario Dante",
                "mario@pizzeriadante.it",
                "+39 06 555666",
                "passaparola",
                4500,
                "nuovo",
            ),
            (
                "Ristorante Il Faro",
                "Sara Costa",
                "sara@ilfaro.it",
                "+39 0586 332211",
                "fiera",
                12000,
                "contattato",
            ),
            (
                "Caffè Letterario",
                "Paolo Tosi",
                "info@caffeletterario.it",
                "+39 02 999888",
                "linkedin",
                3200,
                "qualificato",
            ),
            (
                "Hotel Tre Stelle",
                "Federico Greco",
                "fg@tre-stelle.it",
                "+39 045 776655",
                "referenza cliente",
                18000,
                "trattativa",
            ),
            (
                "Boutique Margot",
                "Margherita Rossi",
                "margot@boutique.it",
                "+39 011 332211",
                "instagram",
                5500,
                "vinto",
            ),
        ]
        lead_docs = [
            {
                "id": gen_id(),
                "user_id": user_id,
                "company_name": cn,
                "contact_name": ct,
                "email": em,
                "phone": ph,
                "source": src,
                "estimated_value": v,
                "status": st,
                "notes": "",
                "created_at": now_iso(),
            }
            for cn, ct, em, ph, src, v, st in leads
        ]
        await self.lead_repo.insert_many([dict(l) for l in lead_docs])

        # Appointments: today + next 7 days
        base = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        appt_data = [
            (clients[0], 0, "Presentazione collezione AI 2026", "Via Brera 12, Milano"),
            (clients[1], 1, "Riunione fornitura tessuti hotel", "Via Lago 5, Como"),
            (clients[2], 1, "Degustazione miscele caffè", "Piazza Vecchia 8, Bergamo"),
            (clients[3], 2, "Follow-up offerta capsule", "Via del Porto 3, Genova"),
            (
                clients[4],
                3,
                "Sopralluogo tecnico cuscinetti",
                "Via Industriale 22, Ravenna",
            ),
            (
                clients[5],
                4,
                "Consegna campionario velluti",
                "Via Tornabuoni 9, Firenze",
            ),
            (
                clients[7],
                6,
                "Visita commerciale trimestrale",
                "Corso Francia 100, Torino",
            ),
        ]
        appts = []
        for cli, day_offset, title, loc in appt_data:
            start = base + timedelta(days=day_offset, hours=(day_offset * 2) % 6)
            appts.append(
                {
                    "id": gen_id(),
                    "user_id": user_id,
                    "client_id": cli["id"],
                    "title": title,
                    "description": f"Incontro presso {cli['company_name']}",
                    "start": start.isoformat(),
                    "end": (start + timedelta(hours=1)).isoformat(),
                    "location": loc,
                    "status": "pianificato",
                    "created_at": now_iso(),
                }
            )
        await self.appointment_repo.insert_many([dict(a) for a in appts])

        # Offers
        offers_data = [
            (
                clients[0],
                mandanti[0],
                "Fornitura velluti collezione P/E 2026",
                [
                    {
                        "product_id": products[0]["id"],
                        "description": "Velluto Sangallo 200gr",
                        "quantity": 50,
                        "unit_price": 38.0,
                        "discount": 5,
                    },
                    {
                        "product_id": products[1]["id"],
                        "description": "Lino Premium 320gr",
                        "quantity": 30,
                        "unit_price": 52.0,
                        "discount": 0,
                    },
                ],
                "accettata",
                -10,
            ),
            (
                clients[1],
                mandanti[1],
                "Fornitura caffè annuale Hotel Belvedere",
                [
                    {
                        "product_id": products[2]["id"],
                        "description": "Miscela Aurora 1kg",
                        "quantity": 200,
                        "unit_price": 24.0,
                        "discount": 8,
                    },
                    {
                        "product_id": products[3]["id"],
                        "description": "Capsule Espresso x100",
                        "quantity": 50,
                        "unit_price": 32.0,
                        "discount": 5,
                    },
                ],
                "inviata",
                -3,
            ),
            (
                clients[4],
                mandanti[2],
                "Fornitura cuscinetti industriali Q1",
                [
                    {
                        "product_id": products[4]["id"],
                        "description": "Cuscinetto SKF 6205",
                        "quantity": 500,
                        "unit_price": 18.5,
                        "discount": 10,
                    },
                ],
                "accettata",
                -25,
            ),
            (
                clients[3],
                mandanti[1],
                "Trattativa caffè ristorazione",
                [
                    {
                        "product_id": products[2]["id"],
                        "description": "Miscela Aurora 1kg",
                        "quantity": 80,
                        "unit_price": 24.0,
                        "discount": 5,
                    },
                ],
                "bozza",
                -1,
            ),
            (
                clients[5],
                mandanti[0],
                "Campionario velluti Boutique Eleonora",
                [
                    {
                        "product_id": products[0]["id"],
                        "description": "Velluto Sangallo 200gr",
                        "quantity": 25,
                        "unit_price": 38.0,
                        "discount": 0,
                    },
                ],
                "inviata",
                -7,
            ),
        ]
        offer_docs = []
        for cli, mand, title, items, status, days_offset in offers_data:
            total = calc_offer_total(items)
            created = (
                datetime.now(timezone.utc) + timedelta(days=days_offset)
            ).isoformat()
            expires = (
                datetime.now(timezone.utc) + timedelta(days=days_offset + 30)
            ).isoformat()
            offer_docs.append(
                {
                    "id": gen_id(),
                    "user_id": user_id,
                    "client_id": cli["id"],
                    "mandante_id": mand["id"],
                    "title": title,
                    "items": items,
                    "total": total,
                    "expires_at": expires,
                    "status": status,
                    "notes": "",
                    "created_at": created,
                }
            )
        await self.offer_repo.insert_many([dict(o) for o in offer_docs])

        # Commissions for accepted offers
        comm_docs = []
        for o in offer_docs:
            if o["status"] == "accettata":
                mand = next(m for m in mandanti if m["id"] == o["mandante_id"])
                amount = o["total"] * mand["commission_rate"] / 100
                comm_docs.append(
                    {
                        "id": gen_id(),
                        "user_id": user_id,
                        "offer_id": o["id"],
                        "client_id": o["client_id"],
                        "mandante_id": o["mandante_id"],
                        "amount": round(amount, 2),
                        "rate": mand["commission_rate"],
                        "status": "incassato" if "Q1" in o["title"] else "maturato",
                        "period": o["created_at"][:7],
                        "created_at": o["created_at"],
                    }
                )
        if comm_docs:
            await self.commission_repo.insert_many([dict(c) for c in comm_docs])

        # Documents
        docs = [
            (clients[0], "Contratto annuale Sartoria Conti", "contratto"),
            (clients[1], "Listino caffè 2026", "altro"),
            (clients[4], "Fattura fornitura cuscinetti Q1", "fattura"),
        ]
        doc_records = [
            {
                "id": gen_id(),
                "user_id": user_id,
                "client_id": cli["id"],
                "name": name,
                "category": cat,
                "url": "",
                "notes": "",
                "created_at": now_iso(),
            }
            for cli, name, cat in docs
        ]
        await self.document_repo.insert_many([dict(d) for d in doc_records])

        # Automations
        autos = [
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Promemoria offerte in scadenza",
                "trigger": "offer_expiring",
                "action": "send_reminder",
                "enabled": True,
                "config": {"days_before": 3},
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Cliente non visitato da 30 giorni",
                "trigger": "no_visit_30d",
                "action": "create_task",
                "enabled": True,
                "config": {},
                "created_at": now_iso(),
            },
            {
                "id": gen_id(),
                "user_id": user_id,
                "name": "Lead inattivo da 7 giorni",
                "trigger": "lead_inactive",
                "action": "send_email",
                "enabled": False,
                "config": {"days": 7},
                "created_at": now_iso(),
            },
        ]
        await self.automation_repo.insert_many([dict(a) for a in autos])
        logger.info("Seed completed.")


seed_service = SeedService()
