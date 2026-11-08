from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserProfile, WeightLog
from ..schemas import ProfileIn, ProfileOut
from ..security import get_current_user
from ..services.recommendations import active_plan

router = APIRouter(prefix="/profile", tags=["Profile"])


def _out(profile: UserProfile, user: User) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    out.email = user.email
    return out


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    if user.profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not set up yet.")
    return _out(user.profile, user)


@router.put("", response_model=ProfileOut)
def upsert_profile(data: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = user.profile
    created = profile is None
    if created:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    weight_changed = created or profile.weight_kg != data.weight_kg
    for field, value in data.model_dump().items():
        setattr(profile, field, value)

    # Keep the weight history in sync with the profile weight
    if weight_changed:
        today = date.today()
        log = db.scalar(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.log_date == today))
        if log:
            log.weight_kg = data.weight_kg
        else:
            db.add(WeightLog(user_id=user.id, log_date=today, weight_kg=data.weight_kg))

    db.commit()
    db.refresh(user)
    active_plan(db, user)  # regenerates the workout plan if goal / level / days changed
    return _out(user.profile, user)
