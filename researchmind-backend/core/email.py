"""Email notification utility for ResearchMind.

Supports two delivery backends, tried in order:
1. Resend (https://resend.com) — set RESEND_API_KEY in .env
2. SMTP — set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env

If neither is configured, send_research_complete_email() is a no-op.
"""

from __future__ import annotations

import smtplib
import ssl
import structlog
from email.message import EmailMessage

from core.config import settings

logger = structlog.get_logger(__name__)


def _send_via_resend(to: str, subject: str, html: str, text: str) -> None:
    """POST to the Resend REST API (no SDK required)."""
    import urllib.request
    import json

    payload = json.dumps({
        "from": settings.NOTIFY_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        status = resp.status
    if status not in (200, 201):
        raise RuntimeError(f"Resend returned HTTP {status}")


def _send_via_smtp(to: str, subject: str, html: str, text: str) -> None:
    """Send via standard SMTP with STARTTLS."""
    msg = EmailMessage()
    msg["From"] = settings.NOTIFY_FROM_EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def send_research_complete_email(
    to_email: str,
    topic: str,
    research_id: str,
    app_url: str = "http://localhost:5173",
) -> None:
    """
    Send a "your research is ready" notification email.

    This function is a no-op when neither RESEND_API_KEY nor SMTP_HOST is
    configured — safe to call unconditionally.
    """
    if not settings.RESEND_API_KEY and not settings.SMTP_HOST:
        return  # Email not configured — silently skip

    report_url = f"{app_url}/research/{research_id}"
    subject = f"Your ResearchMind report is ready: {topic[:60]}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: system-ui, sans-serif; background: #0f0f14; color: #e4e4ed; padding: 40px 20px; max-width: 600px; margin: 0 auto;">
  <h1 style="font-size: 22px; color: #ffffff; margin-bottom: 8px;">Research Complete</h1>
  <p style="color: #9898b0; margin-bottom: 24px;">Your research report on <strong style="color: #ffffff;">{topic}</strong> is ready to view.</p>
  <a href="{report_url}"
     style="display: inline-block; background: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600;">
    View Report →
  </a>
  <p style="color: #55556a; font-size: 12px; margin-top: 32px;">
    ResearchMind · <a href="{report_url}" style="color: #4f46e5;">{report_url}</a>
  </p>
</body>
</html>
"""
    text = f"Your ResearchMind report on '{topic}' is ready.\n\nView it here: {report_url}"

    try:
        if settings.RESEND_API_KEY:
            _send_via_resend(to_email, subject, html, text)
            logger.info("email_sent", via="resend", to=to_email, research_id=research_id)
        elif settings.SMTP_HOST:
            _send_via_smtp(to_email, subject, html, text)
            logger.info("email_sent", via="smtp", to=to_email, research_id=research_id)
    except Exception as exc:
        # Never let email failure surface as a user-visible error
        logger.warning("email_send_failed", to=to_email, research_id=research_id, error=str(exc))
