"""Parse persisted app_settings.value_text flags without DB dependencies."""


def truthy_app_value(value_text: str | None) -> bool | None:
    """Return True/False for known strings, or None if unset/unknown."""
    if value_text is None:
        return None
    s = value_text.strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return None
