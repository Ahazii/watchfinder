"""Persist Everywatch login email/password in app_settings (self-hosted; stored as plaintext)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.models import AppSetting

KEY_EMAIL = "everywatch_login_email"
KEY_PASSWORD = "everywatch_login_password"


def get_everywatch_login_email(db: Session) -> str:
    row = db.get(AppSetting, KEY_EMAIL)
    return (row.value_text or "").strip() if row else ""


def get_everywatch_login_password(db: Session) -> str:
    row = db.get(AppSetting, KEY_PASSWORD)
    return (row.value_text or "") if row else ""


def everywatch_password_configured(db: Session) -> bool:
    return bool(get_everywatch_login_password(db).strip())


def set_everywatch_login_credentials(
    db: Session,
    *,
    email: str | None = None,
    password: str | None = None,
) -> None:
    """
    email / password None = do not change that field.
    password "" clears stored password.
    """
    if email is not None:
        e = email.strip()
        if len(e) > 320:
            e = e[:320]
        row = db.get(AppSetting, KEY_EMAIL)
        if row:
            row.value_text = e
        else:
            db.add(AppSetting(key=KEY_EMAIL, value_text=e))
    if password is not None:
        if len(password) > 2000:
            password = password[:2000]
        row = db.get(AppSetting, KEY_PASSWORD)
        if row:
            row.value_text = password
        else:
            db.add(AppSetting(key=KEY_PASSWORD, value_text=password))
    db.commit()
