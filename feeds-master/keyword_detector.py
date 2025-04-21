def detect_keywords(text, keywords=["party"]):
    """Check if any keywords are in the transcribed text."""
    text_lower = text.lower()
    found_keywords = []
    for keyword in keywords:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)
    return found_keywords