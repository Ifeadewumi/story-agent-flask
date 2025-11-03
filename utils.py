def is_valid_telex_payload(body):
    """
    Validate Telex A2A message payload.
    Expected structure:
    {
      "event": "message_created",
      "message": {"text": "..."}
    }
    """
    return (
        isinstance(body, dict)
        and body.get("event") == "message_created"
        and isinstance(body.get("message"), dict)
        and isinstance(body["message"].get("text"), str)
    )


def make_a2a_response(text):
    """Format a valid A2A response."""
    return {
        "data": {
            "response_type": "in_channel",
            "text": text
        }
    }
