def handle_request(message):
    """Turn an incoming message into a small response."""
    cleaned = normalize(message)
    return {"reply": cleaned}


def normalize(message):
    return message.strip()
