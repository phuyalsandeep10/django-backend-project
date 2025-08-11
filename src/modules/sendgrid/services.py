import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.config.settings import settings

logger = logging.getLogger(__name__)


def send_sendgrid_email(
    from_email: str, to_email: str, subject: str, html_content: str
):
    try:
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
    except Exception as e:
        logger.exception(e)
