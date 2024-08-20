import random
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    print('its working')
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
   try:
        print('Sending OTP...')
        subject = 'ShoeSpectra OTP'
        message = f'Your OTP code is {otp}'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list)
        print('OTP sent successfully.')
   except Exception as e:
        error_message = f'Error sending OTP: {e}'
        print(error_message)
        logger.error(error_message)
    

        
        
    