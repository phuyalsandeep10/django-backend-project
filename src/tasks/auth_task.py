import logging

from src.config.celery import celery_app
from src.config.mail import mail_sender
from src.config.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task
def send_verification_email(email: str, token: str):
    try:
        logger.info("Sending email")
        mail_sender.send(
            subject="Email Verification",
            recipients=[email],
            body_html=f"<p>Email Verification Token: {token}</p>",
            body_text="This is a test email.",
        )
        logger.info("Successful send")
    except Exception as e:
        print("The email ", e)
        logger.exception(e)


@celery_app.task
def send_forgot_password_email(email: str, token: str, frontend_url: str):
    full_link = f"{frontend_url}/forgot-password-verify?email={email}&token={token}"
    print(f"Sending forgot password email to {email} with token {token}")
    mail_sender.send(
        subject="Forgot Password",
        recipients=[email],
        body_html=f"<p>Forgot Password Token: {token} and <a href='{full_link}'>Click here to reset your password. </a></p> ",
        body_text="This is a test email.",
    )
