from twilio.rest import Client

def send_sms_alert(text, found_keywords, phone_numbers, account_sid, auth_token, from_number):
    """Send SMS alert when keywords are detected."""
    client = Client(account_sid, auth_token)
    message = f"ALERT: Keywords {', '.join(found_keywords)} detected in: {text}"
    
    for number in phone_numbers:
        client.messages.create(
            body=message,
            from_=from_number,
            to=number
        )