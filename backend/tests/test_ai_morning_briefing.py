"""
Test per il briefing proattivo dell'assistente AI ('Buongiorno Franco. Hai:
...'), che sostituisce l'attesa passiva di un comando con un saluto che
riassume la situazione della giornata.

Due livelli di test:
1. format_morning_briefing() e _pluralize_it(): logica pura di formattazione,
   nessuna dipendenza dal DB.
2. get_today_brief(): i tre nuovi calcoli (prossimo appuntamento in minuti,
   clienti inattivi da 60+ giorni, previsione fatturato mese), verificati con
   un finto DB in memoria (le query usate sono tutte {"user_id": ...} senza
   operatori complessi, quindi un filtro per uguaglianza è sufficiente).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_morning_briefing.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from services.dashboard_service import DashboardService, _pluralize_it
import core.utils as utils_mod


def run(coro):
    return asyncio.run(coro)


# ---------- _pluralize_it ----------

def test_pluralize_zero_usa_none_label():
    assert _pluralize_it(0, "cliente", "clienti", none_label="Nessun cliente") == "Nessun cliente"


def test_pluralize_uno_usa_singolare():
    assert _pluralize_it(1, "cliente da richiamare", "clienti da richiamare") == "1 cliente da richiamare"


def test_pluralize_molti_usa_plurale():
    assert _pluralize_it(5, "cliente da richiamare", "clienti da richiamare") == "5 clienti da richiamare"


def test_pluralize_zero_senza_none_label_mostra_zero():
    assert _pluralize_it(0, "cliente", "clienti") == "0 clienti"


# ---------- format_morning_briefing ----------

def _base_brief(**overrides):
    brief = {
        "clients_to_call": 5,
        "offers_expiring": 2,
        "payments_to_verify": 3,
        "inactive_clients_60d": 2,
        "next_appointment_minutes": 40,
        "next_appointment_client": "Bar Rossi",
        "revenue_forecast_month": 9500.0,
        "monthly_goal": 10000,
    }
    brief.update(overrides)
    return brief


def test_format_briefing_include_il_saluto_con_nome():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(), "Franco")
    assert text.startswith("Buongiorno Franco.")


def test_format_briefing_senza_nome_usa_saluto_generico():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(), None)
    assert text.startswith("Buongiorno.")


def test_format_briefing_include_tutte_le_metriche():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(), "Franco")
    assert "5 clienti da richiamare" in text
    assert "2 offerte in scadenza" in text
    assert "provvigioni da controllare" in text
    assert "clienti inattivi da oltre 60 giorni" in text
    assert "40 minuti" in text
    assert "Bar Rossi" in text
    assert "Previsione fatturato mese" in text


def test_format_briefing_prossimo_appuntamento_oltre_unora():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(next_appointment_minutes=125), "Franco")
    assert "2h 5min" in text


def test_format_briefing_nessun_appuntamento_in_programma():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(next_appointment_minutes=None, next_appointment_client=None), "Franco",
    )
    assert "Nessun appuntamento in programma" in text


def test_format_briefing_zero_ovunque_usa_frasi_naturali():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(
        clients_to_call=0, offers_expiring=0, payments_to_verify=0, inactive_clients_60d=0,
        next_appointment_minutes=None, next_appointment_client=None,
    ), "Franco")
    assert "Nessun cliente da richiamare" in text
    assert "Nessuna offerta in scadenza" in text
    assert "Nessuna provvigione da controllare" in text
    assert "Nessun cliente inattivo da oltre 60 giorni" in text
    assert "Nessun appuntamento in programma" in text


def test_format_briefing_previsione_sotto_obiettivo():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(revenue_forecast_month=5000.0, monthly_goal=10000), "Franco",
    )
    assert "sotto l'obiettivo" in text


def test_format_briefing_previsione_sopra_obiettivo():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(revenue_forecast_month=15000.0, monthly_goal=10000), "Franco",
    )
    assert "sopra l'obiettivo" in text


# ---------- nuove frasi: visite di oggi, focus cliente, proiezione obiettivo ----------

def test_format_briefing_conta_le_visite_di_oggi_plurale():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(appointments_today=7), "Franco")
    assert "Oggi hai 7 visite in programma." in text


def test_format_briefing_conta_le_visite_di_oggi_singolare():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(appointments_today=1), "Franco")
    assert "Oggi hai 1 visita in programma." in text


def test_format_briefing_nessuna_visita_oggi_frase_naturale():
    service = DashboardService()
    text = service.format_morning_briefing(_base_brief(appointments_today=0), "Franco")
    assert "Oggi non hai visite in programma." in text


def test_format_briefing_suggerisce_focus_client_di_oggi():
    service = DashboardService()
    todays_focus = {
        "client_name": "Rossi Spa", "reason": "expiry_and_inactivity", "days_since_last_order": 20,
    }
    text = service.format_morning_briefing(
        _base_brief(appointments_today=3, todays_focus_client=todays_focus), "Franco",
    )
    assert "Ti consiglio di iniziare da Rossi Spa" in text
    assert "offerta in scadenza" in text
    assert "20 giorni" in text


def test_format_briefing_focus_client_non_menziona_mai_il_traffico():
    """Il pianificatore non ha dati di traffico reale (vedi
    route_optimization_service): il briefing non deve mai fingere di
    saperne qualcosa, per nessuna delle categorie di motivazione."""
    service = DashboardService()
    for reason, extra in [
        ("expiry_and_inactivity", {"days_since_last_order": 10}),
        ("expiry_only", {}),
        ("inactivity_only", {"days_since_last_visit": 45}),
    ]:
        todays_focus = {"client_name": "Rossi Spa", "reason": reason, **extra}
        text = service.format_morning_briefing(
            _base_brief(appointments_today=1, todays_focus_client=todays_focus), "Franco",
        )
        assert "traffic" not in text.lower() and "traffico" not in text.lower()


def test_format_briefing_senza_focus_client_di_oggi_non_lo_menziona():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(appointments_today=3, todays_focus_client=None), "Franco",
    )
    assert "Ti consiglio di iniziare da" not in text


def test_format_briefing_proiezione_obiettivo_se_chiudi_le_offerte():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(offers_expiring=2, projected_pct_if_expiring_closed=96), "Franco",
    )
    assert "Se chiudi le 2 offerte in scadenza raggiungeresti il 96% dell'obiettivo mensile." in text


def test_format_briefing_proiezione_obiettivo_singolare():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(offers_expiring=1, projected_pct_if_expiring_closed=60), "Franco",
    )
    assert "Se chiudi l'offerta in scadenza raggiungeresti il 60%" in text


def test_format_briefing_senza_proiezione_se_nessuna_offerta_in_scadenza():
    service = DashboardService()
    text = service.format_morning_briefing(
        _base_brief(offers_expiring=0, projected_pct_if_expiring_closed=None), "Franco",
    )
    assert "raggiungeresti" not in text


# ---------- get_today_brief: todays_focus_client, offers_expiring_total, proiezione ----------

def test_todays_focus_client_solo_se_ha_una_visita_oggi(monkeypatch):
    """Il cliente prioritario del mese (focus_client) non deve diventare
    'inizia da lui' se oggi non ha alcuna visita in programma. Il cliente
    visitato oggi, per non far scattare a sua volta il ripiego 'più
    trascurato' dentro l'insieme ristretto, ha una visita recente registrata
    (altrimenti risulterebbe lui stesso 'mai visitato', innescando comunque
    un suggerimento — comportamento corretto, ma non quello che questo test
    vuole isolare).

    Tempo congelato a un istante fisso lontano dalla mezzanotte italiana:
    con 'adesso + 1 ora' preso dall'orologio reale, un'esecuzione del test
    tra le 22 e le 24 ora italiana farebbe cadere quell'appuntamento nel
    giorno di calendario SUCCESSIVO (vedi local_date_str/now_local), facendo
    sparire l'appuntamento da 'oggi' e rendendo il test intermittente."""
    import services.dashboard_service as dash_mod

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(dash_mod, "datetime", FakeDatetime)
    monkeypatch.setattr(utils_mod, "datetime", FakeDatetime)
    now = FakeDatetime.now()
    fake_db = FakeDB(
        clients=[
            {"id": "c-priorita", "user_id": "u1", "company_name": "Priorità Mese", "status": "attivo"},
            {"id": "c-oggi", "user_id": "u1", "company_name": "Visita Oggi", "status": "attivo"},
        ],
        appointments=[
            {
                "id": "a-oggi", "user_id": "u1", "client_id": "c-oggi",
                "start": _iso(now + timedelta(hours=1)), "status": "pianificato",
            },
            {  # visita recente: c-oggi non risulta trascurato
                "id": "a-oggi-passata", "user_id": "u1", "client_id": "c-oggi",
                "start": _iso(now - timedelta(days=3)), "status": "pianificato",
            },
        ],
        offers=[{
            "id": "o-1", "user_id": "u1", "client_id": "c-priorita", "status": "inviata",
            "title": "Offerta Priorità", "total": 500,
            "expires_at": _iso(now + timedelta(days=2)),
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["focus_client"]["client_id"] == "c-priorita"  # priorità mensile invariata
    assert brief["todays_focus_client"] is None  # ma non è tra le visite di oggi


def test_todays_focus_client_coincide_se_il_cliente_prioritario_e_tra_le_visite_di_oggi(monkeypatch):
    """Tempo congelato per lo stesso motivo del test precedente (evitare il
    bordo mezzanotte italiana con un appuntamento a 'adesso + 1 ora')."""
    import services.dashboard_service as dash_mod

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(dash_mod, "datetime", FakeDatetime)
    monkeypatch.setattr(utils_mod, "datetime", FakeDatetime)
    now = FakeDatetime.now()
    fake_db = FakeDB(
        clients=[{"id": "c-1", "user_id": "u1", "company_name": "Rossi Spa", "status": "attivo"}],
        appointments=[{
            "id": "a-1", "user_id": "u1", "client_id": "c-1",
            "start": _iso(now + timedelta(hours=1)), "status": "pianificato",
        }],
        offers=[{
            "id": "o-1", "user_id": "u1", "client_id": "c-1", "status": "inviata",
            "title": "Offerta Rossi", "total": 500,
            "expires_at": _iso(now + timedelta(days=2)),
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["todays_focus_client"]["client_id"] == "c-1"
    assert brief["todays_focus_client"]["client_name"] == "Rossi Spa"


def test_offers_expiring_total_e_proiezione_obiettivo(monkeypatch):
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    fake_db = FakeDB(
        clients=[{"id": "c-1", "user_id": "u1", "company_name": "Cliente A", "status": "attivo"}],
        offers=[
            {
                "id": "o-1", "user_id": "u1", "client_id": "c-1", "status": "inviata",
                "title": "Offerta A", "total": 3000, "expires_at": _iso(now + timedelta(days=1)),
            },
            {
                "id": "o-2", "user_id": "u1", "client_id": "c-1", "status": "bozza",
                "title": "Offerta B", "total": 2600, "expires_at": _iso(now + timedelta(days=3)),
            },
        ],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1", "goal_revenue": 10000}))

    assert brief["offers_expiring"] == 2
    assert brief["offers_expiring_total"] == 5600
    # month_revenue_so_far è 0 (nessun ordine/offerta accettata questo mese):
    # (0 + 5600) / 10000 * 100 = 56%
    assert brief["projected_pct_if_expiring_closed"] == 56


def test_nessuna_proiezione_se_nessuna_offerta_in_scadenza(monkeypatch):
    import services.dashboard_service as dash_mod
    fake_db = FakeDB()
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1", "goal_revenue": 10000}))

    assert brief["offers_expiring_total"] == 0
    assert brief["projected_pct_if_expiring_closed"] is None


# ---------- get_today_brief: nuovi calcoli, con un finto DB in memoria ----------

class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, limit):
        return self._docs[:limit]


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query, projection=None):
        matched = [d for d in self._docs if all(d.get(k) == v for k, v in query.items())]
        return FakeCursor(matched)


class FakeDB:
    def __init__(self, clients=None, appointments=None, offers=None, commissions=None, orders=None):
        self.clients = FakeCollection(clients or [])
        self.appointments = FakeCollection(appointments or [])
        self.offers = FakeCollection(offers or [])
        self.commissions = FakeCollection(commissions or [])
        self.orders = FakeCollection(orders or [])


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def test_next_appointment_minutes_calcolato_correttamente(monkeypatch):
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=40)
    fake_db = FakeDB(
        clients=[{"id": "c-1", "user_id": "u1", "company_name": "Bar Rossi", "status": "attivo"}],
        appointments=[{
            "id": "a-1", "user_id": "u1", "client_id": "c-1",
            "start": _iso(start), "status": "pianificato",
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["next_appointment_minutes"] in (39, 40)  # tolleranza di arrotondamento
    assert brief["next_appointment_client"] == "Bar Rossi"


def test_nessun_appuntamento_futuro_da_next_appointment_none(monkeypatch):
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=2)
    fake_db = FakeDB(
        clients=[{"id": "c-1", "user_id": "u1", "company_name": "Bar Rossi", "status": "attivo"}],
        appointments=[{
            "id": "a-1", "user_id": "u1", "client_id": "c-1",
            "start": _iso(past), "status": "pianificato",
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["next_appointment_minutes"] is None


def test_inactive_clients_60d_conta_solo_i_clienti_davvero_trascurati(monkeypatch):
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    fake_db = FakeDB(
        clients=[
            {"id": "c-old", "user_id": "u1", "company_name": "Trascurato", "status": "attivo"},
            {"id": "c-recent", "user_id": "u1", "company_name": "Recente", "status": "attivo"},
            {"id": "c-flagged", "user_id": "u1", "company_name": "GiaInattivo", "status": "inattivo"},
        ],
        appointments=[
            {  # visita di 90 giorni fa: conta come inattivo
                "id": "a-old", "user_id": "u1", "client_id": "c-old",
                "start": _iso(now - timedelta(days=90)), "status": "pianificato",
            },
            {  # visita recente: NON conta
                "id": "a-recent", "user_id": "u1", "client_id": "c-recent",
                "start": _iso(now - timedelta(days=5)), "status": "pianificato",
            },
        ],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    # Solo "c-old" (90gg) e "c-flagged" (mai visitato, ma già status
    # 'inattivo' quindi ESCLUSO dal conteggio: la metrica riguarda clienti
    # attivi trascurati, non quelli già segnati come persi).
    assert brief["inactive_clients_60d"] == 1


def test_revenue_forecast_month_proiezione_lineare(monkeypatch):
    import services.dashboard_service as dash_mod
    # Fissiamo now al giorno 10 di un mese di 30 giorni per un calcolo
    # prevedibile: 1000 fatturati in 10 giorni -> proiezione 3000 sui 30 gg.
    fake_now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    monkeypatch.setattr(dash_mod, "datetime", FakeDatetime)
    # now_local() (usata da get_today_brief per il mese corrente in ora
    # italiana) vive in core.utils, non in dashboard_service: va patchato
    # anche lì, altrimenti userebbe ancora l'orologio reale.
    monkeypatch.setattr(utils_mod, "datetime", FakeDatetime)
    fake_db = FakeDB(
        offers=[{
            "user_id": "u1", "status": "accettata", "total": 1000,
            "created_at": "2026-06-05T10:00:00Z",
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["month_revenue_so_far"] == 1000
    assert brief["revenue_forecast_month"] == 3000.0


def test_appuntamento_senza_cliente_con_orario_naive_non_fa_esplodere_il_brief(monkeypatch):
    """Regressione da un bug reale in produzione: un appuntamento SENZA
    client_id (es. un promemoria personale, non collegato a nessun cliente)
    con 'start' salvato come datetime "naive" (senza fuso orario, es.
    '2026-07-22T10:00:00' invece di '...T10:00:00Z') mandava in errore
    l'intero get_today_brief con 'can't compare offset-naive and
    offset-aware datetimes' — non catturato perché il confronto con `now`
    era fuori dal blocco try/except che avvolgeva solo il parsing.

    Il blocco last_appt_by_client (pre-esistente) non veniva mai raggiunto
    da questo appuntamento perché richiede client_id; il blocco
    next_appointment (nuovo) invece non filtra su client_id ed era il primo
    a incontrare il dato malformato."""
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    naive_start = (now + timedelta(hours=1)).replace(tzinfo=None).isoformat()  # niente 'Z' né offset

    fake_db = FakeDB(appointments=[
        {  # promemoria senza cliente, orario naive: il dato che causava il crash
            "id": "a-naive", "user_id": "u1", "client_id": None,
            "start": naive_start, "status": "pianificato",
        },
    ])
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    # Non deve sollevare alcuna eccezione: l'appuntamento malformato viene
    # scartato (nessun candidato valido), non manda in crash l'intero brief.
    brief = run(service.get_today_brief({"id": "u1"}))

    assert brief["next_appointment_minutes"] is None


def test_appuntamento_di_un_cliente_con_orario_naive_non_fa_esplodere_il_brief(monkeypatch):
    """Stessa classe di bug (naive vs aware), ma sul blocco last_appt_by_client
    (usato da clients_to_call e inactive_clients_60d): un appuntamento
    collegato a un cliente con 'start' naive non deve far esplodere il
    brief, anche se questo blocco esisteva già prima del briefing AI."""
    import services.dashboard_service as dash_mod
    now = datetime.now(timezone.utc)
    naive_start = (now - timedelta(days=5)).replace(tzinfo=None).isoformat()

    fake_db = FakeDB(
        clients=[{"id": "c-1", "user_id": "u1", "company_name": "Bar Rossi", "status": "attivo"}],
        appointments=[{
            "id": "a-naive", "user_id": "u1", "client_id": "c-1",
            "start": naive_start, "status": "pianificato",
        }],
    )
    monkeypatch.setattr(dash_mod, "db", fake_db)
    service = DashboardService()

    brief = run(service.get_today_brief({"id": "u1"}))

    # L'appuntamento naive viene scartato (non conta come "ultima visita"),
    # quindi il cliente risulta senza visite registrate -> va richiamato.
    assert brief["clients_to_call"] == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
