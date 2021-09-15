from email.message import EmailMessage
from smtplib import SMTP_SSL
import threading
from typing import Sequence
from mongo.utils import *
from mongo.config import config

__all__ = ('send_noreply', )


def send(
    from_addr: str,
    password: str,
    to_addrs: Sequence[str],
    subject: str,
    content: str,
):
    SMTP_SERVER = config.get('SMTP.SERVER')
    if SMTP_SERVER is None:
        logger().error('SMTP.SERVER is not set')
        return
    with SMTP_SSL(SMTP_SERVER) as server:
        server.login(from_addr, password)
        msg = EmailMessage()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject
        msg.set_content(content)
        server.send_message(msg, from_addr, to_addrs)


def send_noreply(
    to_addrs: Sequence[str],
    subject: str,
    content: str,
):
    if config['ENV'] == 'development':
        logger().debug('Send email is disabled in dev mode.')
        return
    args = (
        config['SMTP']['NOREPLY'],
        config['SMTP']['NOREPLY_PASSWORD'],
        to_addrs,
        subject,
        content,
    )
    threading.Thread(target=send, args=args).start()
