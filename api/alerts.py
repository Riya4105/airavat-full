# api/alerts.py
# Twilio SMS and WhatsApp alert dispatch
# Fires when a zone crosses HIGH threshold

import os
from twilio.rest import Client

# ── Twilio credentials ─────────────────────────────────────
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_PHONE  = os.environ.get("TWILIO_PHONE")

# ── Registered operators per agency ───────────────────────
OPERATOR_CONTACTS = {
    "coast_guard":      ["+919356850017"],
    "fisheries_kerala": ["+919356850017"],
    "conservation_ngo": ["+919356850017"],
    "thalassa_admin":   ["+919356850017"],
}

def send_sms(to_number: str, message: str) -> dict:
    """Send SMS via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=FROM_PHONE,
            to=to_number
        )
        return {"status": "sent", "sid": msg.sid, "to": to_number}
    except Exception as e:
        return {"status": "failed", "error": str(e), "to": to_number}

# Twilio WhatsApp sandbox number
WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

def send_whatsapp(to_number: str, message: str) -> dict:
    """Send WhatsApp message via Twilio sandbox."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=WHATSAPP_FROM,
            to=f"whatsapp:{to_number}"
        )
        return {"status": "sent", "sid": msg.sid, "to": to_number}
    except Exception as e:
        return {"status": "failed", "error": str(e), "to": to_number}

def format_alert_message(zone_data: dict) -> str:
    """Format zone ESG data into a concise alert message."""
    return (
        f"AIRAVAT 3.0 ALERT\n"
        f"Zone: {zone_data['zone_name']}\n"
        f"Level: {zone_data['alert_level']}\n"
        f"Event: {zone_data['best_match'].replace('_', ' ').title()}\n"
        f"Chain: Step {zone_data['chain_position']} of {zone_data['chain_total']}\n"
        f"Priority: {zone_data['priority']}\n"
        f"SST: {zone_data['latest_sst']}C\n"
        f"Action: Dispatch response team immediately."
    )

def dispatch_alert(zone_data: dict, agency_id: str, channel: str = "sms") -> list:
    """
    Dispatch alert to all operators of an agency.
    channel: 'sms' or 'whatsapp'
    """
    contacts = OPERATOR_CONTACTS.get(agency_id, [])
    if not contacts:
        return [{"status": "no_contacts", "agency": agency_id}]

    message = format_alert_message(zone_data)
    results = []

    for number in contacts:
        if channel == "whatsapp":
            result = send_whatsapp(number, message)
        else:
            result = send_sms(number, message)
        results.append(result)

    return results