import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import jwt
import requests
from requests_oauthlib import OAuth2Session

from core.observability import record_event, Timer
from core.config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI,
    GOOGLE_CALENDAR_SCOPES, JWT_SECRET, JWT_ALG,
)
from core.crypto import encrypt_str, decrypt_str
from core.utils import gen_id, now_iso
from repositories.google_calendar_repository import google_calendar_repository
from repositories.appointment_repository import appointment_repository

logger = logging.getLogger(__name__)

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    def __init__(self, repo=google_calendar_repository, appt_repo=appointment_repository):
        self.repo = repo
        self.appt_repo = appt_repo

    # ------------------------------------------------------------------ #
    # OAuth
    # ------------------------------------------------------------------ #
    def get_auth_url(self, user_id: str) -> str:
        state = jwt.encode(
            {"uid": user_id, "purpose": "gcal_connect",
             "exp": datetime.utcnow() + timedelta(minutes=10)},
            JWT_SECRET, algorithm=JWT_ALG,
        )
        oauth = OAuth2Session(
            GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI,
            scope=GOOGLE_CALENDAR_SCOPES, state=state,
        )
        auth_url, _ = oauth.authorization_url(
            GOOGLE_AUTH_BASE, access_type="offline", prompt="consent",
        )
        return auth_url

    async def handle_oauth_callback(self, code: str, state: str) -> str:
        """Scambia il code per i token, salva la connessione. Ritorna lo user_id collegato."""
        try:
            payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALG])
            if payload.get("purpose") != "gcal_connect":
                raise ValueError("state non valido")
            user_id = payload["uid"]
        except jwt.InvalidTokenError:
            raise ValueError("Stato OAuth non valido o scaduto, riprova la connessione")

        def _exchange():
            oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI)
            token = oauth.fetch_token(
                GOOGLE_TOKEN_URL, client_secret=GOOGLE_CLIENT_SECRET, code=code,
            )
            userinfo = oauth.get(GOOGLE_USERINFO_URL).json()
            return token, userinfo

        token, userinfo = await asyncio.to_thread(_exchange)

        refresh_token = token.get("refresh_token")
        data = {
            "user_id": user_id,
            "google_email": userinfo.get("email", ""),
            "access_token": token["access_token"],
            "access_token_expiry": token.get("expires_at", time.time() + 3000),
            "calendar_id": "primary",
            "connected_at": now_iso(),
        }
        if refresh_token:
            data["refresh_token_enc"] = encrypt_str(refresh_token)
        else:
            # Google non ridà il refresh token se l'utente aveva già acconsentito prima
            # senza prompt=consent forzato: conserviamo quello già salvato, se esiste.
            existing = await self.repo.find_by_user(user_id)
            if not existing or not existing.get("refresh_token_enc"):
                raise ValueError(
                    "Google non ha fornito un refresh token. Disconnetti eventuali "
                    "autorizzazioni precedenti su myaccount.google.com/permissions e riprova."
                )
        await self.repo.upsert(user_id, data)
        return user_id

    async def disconnect(self, user_id: str) -> None:
        await self.repo.delete(user_id)

    async def get_status(self, user_id: str) -> dict:
        conn = await self.repo.find_by_user(user_id)
        if not conn:
            return {"connected": False}
        return {"connected": True, "google_email": conn.get("google_email", "")}

    # ------------------------------------------------------------------ #
    # Access token helpers
    # ------------------------------------------------------------------ #
    async def _valid_access_token(self, conn: dict) -> Optional[str]:
        if conn.get("access_token") and conn.get("access_token_expiry", 0) > time.time() + 30:
            return conn["access_token"]

        def _refresh():
            refresh_token = decrypt_str(conn["refresh_token_enc"])
            resp = requests.post(GOOGLE_TOKEN_URL, data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }, timeout=15)
            resp.raise_for_status()
            return resp.json()

        try:
            result = await asyncio.to_thread(_refresh)
        except requests.HTTPError as e:
            logger.error(f"Refresh token Google fallito per user {conn['user_id']}: {e}")
            return None
        access_token = result["access_token"]
        expiry = time.time() + result.get("expires_in", 3600) - 60
        await self.repo.upsert(conn["user_id"], {
            "access_token": access_token, "access_token_expiry": expiry,
        })
        return access_token

    # ------------------------------------------------------------------ #
    # Push: Salesfly -> Google Calendar
    # ------------------------------------------------------------------ #
    @staticmethod
    def _event_body(appointment: dict) -> dict:
        start = appointment["start"]
        end = appointment.get("end")
        if not end:
            try:
                end = (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat()
            except ValueError:
                end = start
        return {
            "summary": appointment.get("title", "Appuntamento"),
            "description": appointment.get("description", "") or "",
            "location": appointment.get("location", "") or "",
            "start": {"dateTime": start, "timeZone": "Europe/Rome"},
            "end": {"dateTime": end, "timeZone": "Europe/Rome"},
            "extendedProperties": {"private": {"salesfly_appointment_id": appointment["id"]}},
        }

    async def push_create(self, user_id: str, appointment: dict) -> None:
        conn = await self.repo.find_by_user(user_id)
        if not conn:
            return
        token = await self._valid_access_token(conn)
        if not token:
            return

        def _create():
            return requests.post(
                f"{CALENDAR_API_BASE}/calendars/{conn['calendar_id']}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=self._event_body(appointment), timeout=15,
            )

        try:
            resp = await asyncio.to_thread(_create)
            resp.raise_for_status()
            event = resp.json()
            await self.appt_repo.update(appointment["id"], user_id, {"google_event_id": event["id"]})
        except requests.HTTPError as e:
            logger.error(f"Push create evento Google fallito per user {user_id}: {e}")

    async def push_update(self, user_id: str, appointment: dict) -> None:
        google_event_id = appointment.get("google_event_id")
        if not google_event_id:
            await self.push_create(user_id, appointment)
            return
        conn = await self.repo.find_by_user(user_id)
        if not conn:
            return
        token = await self._valid_access_token(conn)
        if not token:
            return

        def _update():
            return requests.patch(
                f"{CALENDAR_API_BASE}/calendars/{conn['calendar_id']}/events/{google_event_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=self._event_body(appointment), timeout=15,
            )

        try:
            resp = await asyncio.to_thread(_update)
            if resp.status_code == 404:
                # L'evento non esiste più su Google: ricrealo
                await self.push_create(user_id, appointment)
                return
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"Push update evento Google fallito per user {user_id}: {e}")

    async def push_delete(self, user_id: str, google_event_id: Optional[str]) -> None:
        if not google_event_id:
            return
        conn = await self.repo.find_by_user(user_id)
        if not conn:
            return
        token = await self._valid_access_token(conn)
        if not token:
            return

        def _delete():
            return requests.delete(
                f"{CALENDAR_API_BASE}/calendars/{conn['calendar_id']}/events/{google_event_id}",
                headers={"Authorization": f"Bearer {token}"}, timeout=15,
            )

        try:
            resp = await asyncio.to_thread(_delete)
            if resp.status_code not in (200, 204, 404, 410):
                resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"Push delete evento Google fallito per user {user_id}: {e}")

    # ------------------------------------------------------------------ #
    # Pull: Google Calendar -> Salesfly (polling con sync token incrementale)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _appointment_from_event(user_id: str, event: dict) -> dict:
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        return {
            "user_id": user_id,
            "title": event.get("summary", "Appuntamento"),
            "description": event.get("description", "") or "",
            "location": event.get("location", "") or "",
            "start": start,
            "end": end,
            "google_event_id": event["id"],
        }

    async def _pull_for_connection(self, conn: dict) -> None:
        user_id = conn["user_id"]
        token = await self._valid_access_token(conn)
        if not token:
            return

        params = {"singleEvents": "true", "showDeleted": "true", "maxResults": 250}
        sync_token = conn.get("sync_token")
        if sync_token:
            params["syncToken"] = sync_token
        else:
            params["timeMin"] = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"

        events = []
        next_page_token = None
        next_sync_token = None
        full_resync_needed = False

        while True:
            page_params = dict(params)
            if next_page_token:
                page_params["pageToken"] = next_page_token

            def _list():
                return requests.get(
                    f"{CALENDAR_API_BASE}/calendars/{conn['calendar_id']}/events",
                    headers={"Authorization": f"Bearer {token}"}, params=page_params, timeout=15,
                )

            resp = await asyncio.to_thread(_list)
            if resp.status_code == 410:
                # sync token scaduto/non valido: serve un resync completo la prossima volta
                full_resync_needed = True
                break
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                logger.error(f"Pull eventi Google fallito per user {user_id}: {e}")
                return
            data = resp.json()
            events.extend(data.get("items", []))
            next_page_token = data.get("nextPageToken")
            next_sync_token = data.get("nextSyncToken", next_sync_token)
            if not next_page_token:
                break

        if full_resync_needed:
            await self.repo.upsert(user_id, {"sync_token": None})
            return

        for event in events:
            try:
                await self._apply_event(user_id, event)
            except Exception as e:
                logger.error(f"Errore applicando evento Google {event.get('id')} per user {user_id}: {e}")

        if next_sync_token:
            await self.repo.upsert(user_id, {"sync_token": next_sync_token})

    async def _apply_event(self, user_id: str, event: dict) -> None:
        google_event_id = event["id"]
        local = await self.appt_repo.find_by_google_event_id(user_id, google_event_id)

        if event.get("status") == "cancelled":
            if local:
                await self.appt_repo.delete(local["id"], user_id)
            return

        fields = self._appointment_from_event(user_id, event)
        if not fields["start"]:
            return  # evento senza orario valorizzato, ignoriamo

        if local:
            await self.appt_repo.update(local["id"], user_id, {
                "title": fields["title"], "description": fields["description"],
                "location": fields["location"], "start": fields["start"], "end": fields["end"],
            })
        else:
            doc = {
                "id": gen_id(), "user_id": user_id, "status": "pianificato",
                "client_id": None, "created_at": now_iso(), **fields,
            }
            await self.appt_repo.insert(doc)

    async def sync_now(self, user_id: str) -> None:
        conn = await self.repo.find_by_user(user_id)
        if conn:
            await self._pull_for_connection(conn)

    async def sync_all_connected_accounts(self) -> None:
        connections = await self.repo.find_all()
        for conn in connections:
            try:
                with Timer() as t:
                    await self._pull_for_connection(conn)
                await record_event(
                    "calendar_sync", "success",
                    user_id=conn.get("user_id"), duration_ms=round(t.duration_ms, 1),
                )
            except Exception as e:
                logger.error(f"Sync periodico fallito per user {conn.get('user_id')}: {e}")
                await record_event(
                    "calendar_sync", "failure",
                    user_id=conn.get("user_id"), error=str(e)[:300],
                )


google_calendar_service = GoogleCalendarService()
