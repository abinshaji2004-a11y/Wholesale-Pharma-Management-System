from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order

@receiver(post_save, sender=Order)
def order_created_notification(sender, instance, created, **kwargs):
    if created:
        # 1. Email Notification
        subject = f"Order Confirmation - Abin Pharma (#{instance.order_number})"
        message = f"Dear {instance.user.first_name},\n\nYour order {instance.order_number} has been placed successfully.\nTotal Amount: Rs. {instance.total_amount}\n\nThank you for choosing Abin Pharma."
        recipient_list = [instance.user.email] if instance.user.email else []
        
        if recipient_list:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

        # 2. WhatsApp Notification (via Twilio)
        phone = getattr(instance.user, 'phone_number', None)
        if phone and hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
            try:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                wa_body = f"Hello from Abin Pharma! Your order #{instance.order_number} for Rs.{instance.total_amount} is confirmed."
                
                # Format phone to E.164 if needed, assuming it's valid
                client.messages.create(
                    body=wa_body,
                    from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                    to=f"whatsapp:+91{phone}" # Assuming Indian numbers
                )
            except Exception as e:
                print(f"Failed to send WhatsApp: {e}")
