from datetime import datetime, timezone


def is_subscription_active(user: dict) -> bool:
    """Vero se l'utente può usare l'app: abbonamento attivo oppure trial non ancora scaduto.

    Vive in core/ (non in services/) perché deve essere importabile da core/security.py
    senza creare una dipendenza circolare core -> services.
    """
    status = user.get("subscription_status", "trial")
    if status == "active":
        return True
    if status == "trial":
        trial_end = user.get("trial_ends_at", "")
        try:
            end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < end
        except Exception:
            return True
    return False
