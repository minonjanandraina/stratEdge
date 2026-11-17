import uuid
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import FormView, View, TemplateView
from django.urls import reverse_lazy

from django.contrib.auth.forms import PasswordResetForm
from config.mail import send_password_reset_email
from .models import Department, EmailConfirmation
from .utils import send_confirmation_email


class CustomPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        reset_url = (
            f"{context['protocol']}://{context['domain']}"
            f"/accounts/password-reset/confirm/{context['uid']}/{context['token']}/"
        )
        send_password_reset_email(to_email, reset_url)


class RegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False, label='Prénom')
    last_name = forms.CharField(max_length=150, required=False, label='Nom')
    username = forms.CharField(max_length=150, label='Identifiant')
    email = forms.EmailField(required=True, label='Email')
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label='Département',
        empty_label='-- Choisir un département --',
    )
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8, label='Mot de passe')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmer le mot de passe')

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse email.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=d['username'],
            email=d['email'],
            password=d['password1'],
            first_name=d.get('first_name', ''),
            last_name=d.get('last_name', ''),
            is_active=False,
        )


class RegisterFrontView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('project-list-front')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        department = form.cleaned_data.get('department')
        if department:
            user.profile.department = department
            user.profile.save(update_fields=['department'])
        confirmation = EmailConfirmation.objects.create(user=user)
        try:
            send_confirmation_email(user, confirmation.token, self.request)
        except Exception:
            pass
        self.request.session['pending_confirmation_email'] = user.email
        return redirect('confirm-sent')


class ConfirmSentView(TemplateView):
    template_name = 'accounts/confirm_sent.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['email'] = self.request.session.get('pending_confirmation_email', '')
        return ctx


class VerifyEmailView(View):
    def get(self, request, token):
        try:
            confirmation = EmailConfirmation.objects.select_related('user').get(token=token)
        except EmailConfirmation.DoesNotExist:
            return render(request, 'accounts/verify_failed.html', {'reason': 'invalid'})

        if confirmation.is_verified:
            return render(request, 'accounts/verify_failed.html', {'reason': 'already_used'})

        if confirmation.is_expired():
            return render(request, 'accounts/verify_failed.html', {
                'reason': 'expired',
                'email': confirmation.user.email,
            })

        confirmation.is_verified = True
        confirmation.save(update_fields=['is_verified'])
        user = confirmation.user
        user.is_active = True
        user.save(update_fields=['is_active'])

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Bienvenue {user.get_full_name() or user.username} ! Votre compte est activé.')
        return redirect('project-list-front')


class ResendConfirmationView(View):
    def post(self, request):
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email__iexact=email, is_active=False)
                EmailConfirmation.objects.filter(user=user).delete()
                confirmation = EmailConfirmation.objects.create(user=user)
                try:
                    send_confirmation_email(user, confirmation.token, request)
                except Exception:
                    pass
            except User.DoesNotExist:
                pass  # don't reveal whether email exists
        request.session['pending_confirmation_email'] = email
        return redirect('confirm-sent')
