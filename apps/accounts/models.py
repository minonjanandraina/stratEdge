import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('pm', 'Chef de projet'),
    ('member', 'Membre'),
    ('viewer', 'Lecteur'),
]


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nom')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Département'
        verbose_name_plural = 'Départements'
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='members',
        verbose_name='Département',
    )
    timezone = models.CharField(max_length=50, default='UTC')
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_role_display()})'



class EmailConfirmation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_confirmation')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Confirmation email'
        verbose_name_plural = 'Confirmations email'

    def __str__(self):
        return f'Confirmation — {self.user.email}'

    def is_expired(self):
        expiry_hours = getattr(settings, 'EMAIL_CONFIRMATION_EXPIRY_HOURS', 24)
        return (timezone.now() - self.created_at).total_seconds() > expiry_hours * 3600
