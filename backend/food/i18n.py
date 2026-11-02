def localized(obj, field, lang):
    if lang == "bn":
        val = getattr(obj, f"{field}_bn", "") or ""
        if val:
            return val
    return getattr(obj, field, "")
