from django.conf import settings
from django.template.loader import render_to_string


def send_confirmation_email(user, token, request):
    from config.mail import send_email

    site_url = getattr(settings, 'SITE_URL', None) or request.build_absolute_uri('/').rstrip('/')
    link = f"{site_url}/accounts/verify-email/{token}/"
    expiry_hours = getattr(settings, 'EMAIL_CONFIRMATION_EXPIRY_HOURS', 24)

    subject = "Confirmez votre adresse email — StratEdge"
    html_message = render_to_string('accounts/email_confirm.html', {
        'user': user,
        'link': link,
        'expiry_hours': expiry_hours,
        'site_url': site_url,
    })

    send_email(subject, [user.email], html_message)
