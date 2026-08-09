from datetime import date, timedelta

# Solo festività nazionali fisse + Pasquetta (mobile, calcolata): niente
# festività patronali locali (variano per città, es. Sant'Ambrogio a
# Milano) — semplificazione dichiarata, non una svista. Usato solo per il
# conteggio ferie "festivita" (vedi models.leave_settings), non per altro.
ITALIAN_HOLIDAYS_FIXED = (
    (1, 1),   # Capodanno
    (1, 6),   # Epifania
    (4, 25),  # Liberazione
    (5, 1),   # Festa dei Lavoratori
    (6, 2),   # Festa della Repubblica
    (8, 15),  # Ferragosto
    (11, 1),  # Ognissanti
    (12, 8),  # Immacolata Concezione
    (12, 25),  # Natale
    (12, 26),  # Santo Stefano
)


def easter_sunday(year: int) -> date:
    """Algoritmo di Gauss/Meeus (anonymous Gregorian algorithm) per la data
    della Pasqua: nessuna dipendenza esterna, standard e verificato."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def is_italian_holiday(d: date) -> bool:
    if (d.month, d.day) in ITALIAN_HOLIDAYS_FIXED:
        return True
    return d == easter_sunday(d.year) + timedelta(days=1)  # Pasquetta
