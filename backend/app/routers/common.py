from datetime import date, timedelta

from fastapi import HTTPException


def resolve_date(d: date | None) -> date:
    """Use the client's local date when given (avoids UTC/IST mismatches)."""
    today = date.today()
    if d is None:
        return today
    # Allow +1 day for clients ahead of the server's timezone
    if d > today + timedelta(days=1):
        raise HTTPException(422, "Date cannot be in the future.")
    if d < today - timedelta(days=366 * 2):
        raise HTTPException(422, "Date is too far in the past.")
    return d
