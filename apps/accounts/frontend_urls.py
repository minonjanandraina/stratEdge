from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import frontend_views
from .frontend_views import CustomPasswordResetForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', frontend_views.RegisterFrontView.as_view(), name='register'),
    path('confirm-sent/', frontend_views.ConfirmSentView.as_view(), name='confirm-sent'),
    path('verify-email/<uuid:token>/', frontend_views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-confirmation/', frontend_views.ResendConfirmationView.as_view(), name='resend-confirmation'),

    # Réinitialisation mot de passe
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        form_class=CustomPasswordResetForm,
        success_url=reverse_lazy('password-reset-done'),
    ), name='password-reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password-reset-done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('password-reset-complete'),
    ), name='password-reset-confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password-reset-complete'),
]
