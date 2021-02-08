import logging
import os
import textwrap
from django.conf import settings
from django.core.mail import EmailMessage

from core.models import User


logger = logging.getLogger(__name__)


def allowed_to_send_mail():
    """
    Checks for allowed to send mail or not.

    Returns:
        Boolean value.
    """
    if settings.USE_EMAIL_SERVICE == 'True':
        return True

    return False


def construct_mail(mail, send_to_email=None, otp=None):
    """
    Constructs an email and applies overrides as needed.
    """
    if mail is None:
        mail = {}

    mail['subject'] = "Verify OTP - ITT-ENPHASE"
    mail['from_email'] = mail.get('from_email', settings.DEFAULT_FROM_EMAIL)
    mail['reply_to'] = mail.get('reply_to', settings.REPLY_TO_EMAIL)
    mail['receipient'] = send_to_email
    mail["message"] = textwrap.dedent(f"""
            Here is your OTP to login into ITT-ENPHASE -
            OTP ::  "{otp}"
            <br/>Note - Please don't share this OTP with anyone
    """)

    return mail


def itt_send_mail(mail=None, send_to_email=None, otp=None):
    """
    Sends an email. This is wrapper around django's EmailMessage instance.
    """
    status = 0

    if not allowed_to_send_mail():
        return status

    # print(f"\n\n===email==== {send_to_email}=========\n\n")
    # print(f"\n\n====password===={otp}========\n\n")
    mail = construct_mail(mail, send_to_email, otp)

    try:
        email_message = EmailMessage(
            subject=mail.get('subject'),
            body=mail.get('message'),
            from_email=mail.get('from_email'),
            to=[mail.get('reply_to')],
            reply_to=[mail.get('receipient')],
        )
        # print(f"\n\n====email_message===={email_message}========\n\n")
        status = email_message.send(fail_silently=False)
    except Exception as e:
        logger.exception('Error occurred on sending email')

    return status
