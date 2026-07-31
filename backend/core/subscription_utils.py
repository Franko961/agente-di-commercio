from datetime import datetime, timezone


def is_subscription_active(user: dict) -> bool:
    """Vero se l'utente può usare l'app: abbonamento attivo oppure trial non ancora scaduto.

    Vive in core/ (non in services/) perché deve essere importabile da core/security.py
    senza creare una dipendenza circolare core -> services.
    """
    status = user.get("subscription_status", "trial")
    if status == "active":
        # Un utente che ha disdetto resta 'active' finché non finisce il
        # periodo già pagato (cancel_at, impostato da cancel_subscription):
        # è così che manteniamo la promessa "accesso fino a fine periodo"
        # invece di tagliarlo subito alla richiesta di disdetta.
        cancel_at = user.get("cancel_at")
        if cancel_at:
            try:
                end = datetime.fromisoformat(cancel_at.replace("Z", "+00:00"))
                return datetime.now(timezone.utc) < end
            except Exception:
                return True
        return True
    if status == "trial":
        trial_end = user.get("trial_ends_at", "")
        try:
            end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < end
        except Exception:
            return True
    return False
