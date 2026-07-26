from datetime import datetime, timedelta, timezone

from core.database import db


class HealthService:
    """Aggrega la telemetria raccolta in api_metrics_minute e system_events
    per rispondere concretamente alle domande operative di un SaaS in
    produzione: quale endpoint è lento, quale tasso di errore ha, quante
    chiamate AI falliscono e quanto costano, quante email non vengono
    consegnate, quante sincronizzazioni Calendar falliscono.

    Le aggregazioni girano lato MongoDB (pipeline $group), non caricando i
    documenti in Python: con giorni/settimane di traffico i bucket per
    minuto possono essere molte migliaia di documenti."""

    async def get_health(self, hours: int = 24) -> dict:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        endpoints = await db.api_metrics_minute.aggregate([
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": {"method": "$method", "path": "$path"},
                "count": {"$sum": "$count"},
                "sum_duration_ms": {"$sum": "$sum_duration_ms"},
                "max_duration_ms": {"$max": "$max_duration_ms"},
                "status_4xx": {"$sum": {"$ifNull": ["$status_4xx", 0]}},
                "status_5xx": {"$sum": {"$ifNull": ["$status_5xx", 0]}},
            }},
            {"$project": {
                "_id": 0,
                "method": "$_id.method",
                "path": "$_id.path",
                "count": 1,
                "avg_duration_ms": {"$round": [{"$divide": ["$sum_duration_ms", "$count"]}, 1]},
                "max_duration_ms": {"$round": ["$max_duration_ms", 1]},
                "status_4xx": 1,
                "status_5xx": 1,
                "error_rate_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": [{"$add": ["$status_4xx", "$status_5xx"]}, "$count"]}, 100]},
                        1,
                    ]
                },
            }},
            {"$sort": {"avg_duration_ms": -1}},
        ]).to_list(200)

        slowest = sorted(endpoints, key=lambda e: e["avg_duration_ms"], reverse=True)[:10]
        most_errors = sorted(endpoints, key=lambda e: e["status_5xx"] + e["status_4xx"], reverse=True)[:10]
        most_errors = [e for e in most_errors if e["status_4xx"] + e["status_5xx"] > 0]

        ai_stats = await self._category_stats("ai_call", since, extra_sum_fields=["cost_usd", "tokens_in", "tokens_out"])
        email_stats = await self._category_stats("email_send", since)
        calendar_stats = await self._category_stats("calendar_sync", since)
        automation_stats = await self._category_stats("automation_run", since)

        return {
            "window_hours": hours,
            "endpoints": {
                "slowest": slowest,
                "most_errors": most_errors,
                "total_requests": sum(e["count"] for e in endpoints),
            },
            "ai": ai_stats,
            "email": email_stats,
            "calendar_sync": calendar_stats,
            "automation_run": automation_stats,
        }

    async def _category_stats(self, category: str, since, extra_sum_fields=None) -> dict:
        group_stage = {
            "_id": "$status",
            "count": {"$sum": 1},
        }
        for field in (extra_sum_fields or []):
            group_stage[f"sum_{field}"] = {"$sum": {"$ifNull": [f"${field}", 0]}}

        rows = await db.system_events.aggregate([
            {"$match": {"category": category, "created_at": {"$gte": since}}},
            {"$group": group_stage},
        ]).to_list(10)

        by_status = {r["_id"]: r for r in rows}
        success = by_status.get("success", {}).get("count", 0)
        failure = by_status.get("failure", {}).get("count", 0)
        total = success + failure
        result = {
            "total": total,
            "success": success,
            "failure": failure,
            "failure_rate_pct": round((failure / total) * 100, 1) if total else 0.0,
        }
        for field in (extra_sum_fields or []):
            result[field] = round(
                by_status.get("success", {}).get(f"sum_{field}", 0)
                + by_status.get("failure", {}).get(f"sum_{field}", 0),
                6,
            )
        return result


health_service = HealthService()
