import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from decouple import config as env_config

logger = logging.getLogger(__name__)

SMTP_SERVER = "mail.pamf.mg"
SMTP_PORT   = 25
SENDER      = "no-reply@pamf.mg"
SITE_URL    = env_config('SITE_URL', default='http://localhost:8000')

# ── Couleurs par type de notification ────────────────────────────────────────

_NOTIF_STYLE = {
    'task_assigned':        ('#007AFF', '#EFF6FF', '📋'),
    'deadline_j3':          ('#FF9500', '#FFF7ED', '📅'),
    'deadline_j1':          ('#FF9500', '#FFF7ED', '⏰'),
    'deadline_j0':          ('#FF3B30', '#FFF0F0', '🚨'),
    'task_overdue':         ('#FF3B30', '#FFF0F0', '⚠️'),
    'project_deadline_j7':  ('#FF9500', '#FFF7ED', '📌'),
    'kpi_spi_alert':        ('#FF3B30', '#FFF0F0', '📉'),
    'meeting_reminder':     ('#5856D6', '#F3F2FF', '📆'),
    'task_note_added':      ('#007AFF', '#EFF6FF', '💬'),
    'project_weekly_update': ('#5856D6', '#F3F2FF', '🗓️'),
}
_DEFAULT_STYLE = ('#007AFF', '#EFF6FF', '🔔')


# ── Helpers HTML ─────────────────────────────────────────────────────────────

def _base(content_html):
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#F5F5F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <div style="max-width:560px;margin:40px auto;padding:0 16px;">
    <div style="background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08),0 12px 40px rgba(0,0,0,0.06);">

      <div style="background:#fff;padding:28px 40px 20px;text-align:center;border-bottom:1px solid rgba(0,0,0,0.07);">
        <img src="{SITE_URL}/static/img/logo.png" alt="StratEdge"
             style="height:56px;width:auto;object-fit:contain;display:block;margin:0 auto;">
      </div>

      <div style="padding:36px 40px;">
        {content_html}
      </div>

      <div style="padding:20px 40px;background:#F5F5F7;text-align:center;">
        <p style="margin:0;font-size:12px;color:#AEAEB2;line-height:1.6;">
          Ce message est généré automatiquement — ne pas répondre.<br>
          &copy; StratEdge — DFS Project Management
        </p>
      </div>

    </div>
  </div>
</body>
</html>"""


def _btn(label, url, color='#007AFF'):
    return (
        f'<div style="text-align:center;margin:28px 0;">'
        f'<a href="{url}" style="display:inline-block;background:{color};color:#fff;'
        f'text-decoration:none;padding:14px 36px;border-radius:12px;font-size:15px;'
        f'font-weight:600;letter-spacing:-0.1px;">{label}</a></div>'
    )


def _divider():
    return '<hr style="border:none;border-top:1px solid rgba(0,0,0,0.07);margin:24px 0;">'


def _link_fallback(url):
    return (
        f'<p style="font-size:12px;color:#AEAEB2;line-height:1.5;word-break:break-all;">'
        f'Si le bouton ne fonctionne pas, copiez ce lien :<br>'
        f'<a href="{url}" style="color:#007AFF;text-decoration:none;">{url}</a></p>'
    )


# ── Envoi bas niveau ──────────────────────────────────────────────────────────

def send_email(subject, recipients, html_body, attachment=None, filename=None):
    msg = MIMEMultipart()
    msg['From']    = SENDER
    msg['To']      = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    if attachment:
        part = MIMEApplication(attachment, _subtype="xlsx")
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.ehlo()
            s.sendmail(SENDER, recipients, msg.as_string())
            logger.info("Email envoyé avec succès à %s", recipients)
    except Exception as e:
        logger.error("Erreur envoi mail à %s : %s", recipients, e)


# ── Emails transactionnels ────────────────────────────────────────────────────

def send_activation_email(user_email, activation_link):
    subject = "Activation de votre compte — StratEdge"
    content = f"""
        <p style="font-size:16px;font-weight:600;color:#1D1D1F;margin:0 0 12px;">Bienvenue sur StratEdge 👋</p>
        <p style="font-size:14px;color:#6E6E73;line-height:1.6;margin:0 0 24px;">
            Merci pour votre inscription. Cliquez sur le bouton ci-dessous pour activer votre
            compte et commencer à gérer vos projets.
        </p>
        {_btn("Activer mon compte", activation_link)}
        {_divider()}
        {_link_fallback(activation_link)}
    """
    send_email(subject, [user_email], _base(content))


def send_password_reset_email(user_email, reset_link):
    subject = "Réinitialisation de votre mot de passe — StratEdge"
    content = f"""
        <p style="font-size:16px;font-weight:600;color:#1D1D1F;margin:0 0 12px;">Mot de passe oublié ?</p>
        <p style="font-size:14px;color:#6E6E73;line-height:1.6;margin:0 0 24px;">
            Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte.
            Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe.
        </p>
        {_btn("Réinitialiser mon mot de passe", reset_link)}
        {_divider()}
        <p style="font-size:13px;color:#6E6E73;line-height:1.6;margin:0 0 16px;">
            Si vous n'avez pas demandé cette action, ignorez cet email — votre mot de passe
            restera inchangé.
        </p>
        {_link_fallback(reset_link)}
    """
    send_email(subject, [user_email], _base(content))


# ── Email de notification générique ──────────────────────────────────────────

def send_notification_email(recipient_email, title, message, notif_type=None):
    color, bg, icon = _NOTIF_STYLE.get(notif_type, _DEFAULT_STYLE)
    content = f"""
        <div style="background:{bg};border-left:4px solid {color};border-radius:10px;
                    padding:16px 20px;margin-bottom:24px;">
            <p style="margin:0;font-size:15px;font-weight:600;color:#1D1D1F;">{icon}&nbsp;{title}</p>
        </div>
        <p style="font-size:14px;color:#6E6E73;line-height:1.6;margin:0 0 24px;">{message}</p>
        {_btn("Voir sur StratEdge", SITE_URL, color)}
    """
    send_email(f'[StratEdge] {title}', [recipient_email], _base(content))


# ── Email nouvelle note de tâche ─────────────────────────────────────────────

def send_task_note_email(recipients, project, task, note):
    import html as _html
    author_name = note.created_by.get_full_name() or note.created_by.username
    project_url = f"{SITE_URL}/projects/{project.id}/"
    note_html = _html.escape(note.content).replace('\n', '<br>')
    content = f"""
        <p style="font-size:16px;font-weight:600;color:#1D1D1F;margin:0 0 4px;">💬 Nouvelle note ajoutée</p>
        <p style="font-size:13px;color:#6E6E73;margin:0 0 24px;">
            Par <strong>{_html.escape(author_name)}</strong>
        </p>
        <div style="display:flex;gap:12px;margin-bottom:16px;">
          <div style="flex:1;background:#F5F5F7;border-radius:10px;padding:14px 16px;">
            <p style="margin:0 0 4px;font-size:11px;font-weight:600;color:#AEAEB2;text-transform:uppercase;letter-spacing:0.5px;">Projet</p>
            <p style="margin:0;font-size:14px;font-weight:600;color:#1D1D1F;">{_html.escape(project.name)}</p>
          </div>
          <div style="flex:1;background:#F5F5F7;border-radius:10px;padding:14px 16px;">
            <p style="margin:0 0 4px;font-size:11px;font-weight:600;color:#AEAEB2;text-transform:uppercase;letter-spacing:0.5px;">Tâche</p>
            <p style="margin:0;font-size:14px;font-weight:600;color:#1D1D1F;">{_html.escape(task.name)}</p>
          </div>
        </div>
        <div style="background:#EFF6FF;border-left:4px solid #007AFF;border-radius:0 10px 10px 0;padding:16px 20px;margin-bottom:28px;">
            <p style="margin:0 0 8px;font-size:11px;font-weight:600;color:#AEAEB2;text-transform:uppercase;letter-spacing:0.5px;">Contenu de la note</p>
            <p style="margin:0;font-size:14px;color:#1D1D1F;line-height:1.7;">{note_html}</p>
        </div>
        {_btn("Voir la tâche", project_url)}
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    send_email(
        f'[StratEdge] Nouvelle note — {task.name}',
        recipients,
        _base(content),
    )


# ── Rapport de réconciliation ─────────────────────────────────────────────────

def send_reconciliation_job_report(dt, results, recipients):
    failed_steps = [
        (step, res)
        for entry in results
        for step, res in entry.items()
        if not (isinstance(res, dict) and res.get("code") == 200)
    ]
    all_ok = len(failed_steps) == 0

    if all_ok:
        subject       = f"[Réconciliation] Succès — {dt}"
        badge_color   = '#34C759'
        badge_bg      = '#F0FFF4'
        badge_label   = '✓ SUCCÈS'
        intro         = f"La réconciliation du <strong>{dt}</strong> s'est terminée avec succès."
    else:
        subject       = f"[Réconciliation] ÉCHEC — {dt}"
        badge_color   = '#FF3B30'
        badge_bg      = '#FFF0F0'
        badge_label   = '✕ ÉCHEC'
        intro         = f"La réconciliation du <strong>{dt}</strong> a rencontré des erreurs."

    rows_html = ""
    for entry in results:
        for step_name, res in entry.items():
            ok          = isinstance(res, dict) and res.get("code") == 200
            row_color   = '#34C759' if ok else '#FF3B30'
            row_bg      = '#F0FFF4' if ok else '#FFF0F0'
            label       = '✓ OK' if ok else '✕ ÉCHEC'
            msg_text    = res.get("message", str(res)) if isinstance(res, dict) else str(res)
            rows_html  += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(0,0,0,0.06);
                         font-size:13px;color:#1D1D1F;">{step_name}</td>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(0,0,0,0.06);">
                <span style="display:inline-block;background:{row_bg};color:{row_color};
                             font-weight:600;font-size:12px;padding:3px 10px;
                             border-radius:20px;">{label}</span>
              </td>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(0,0,0,0.06);
                         font-size:12px;color:#6E6E73;">{msg_text}</td>
            </tr>"""

    content = f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
            <p style="margin:0;font-size:16px;font-weight:600;color:#1D1D1F;">
                Rapport de réconciliation — {dt}
            </p>
            <span style="display:inline-block;background:{badge_bg};color:{badge_color};
                         font-weight:700;font-size:13px;padding:4px 14px;
                         border-radius:20px;">{badge_label}</span>
        </div>
        <p style="font-size:14px;color:#6E6E73;line-height:1.6;margin:0 0 20px;">{intro}</p>
        <table style="width:100%;border-collapse:collapse;border:1px solid rgba(0,0,0,0.08);border-radius:10px;overflow:hidden;">
            <thead>
                <tr style="background:#F5F5F7;">
                    <th style="padding:10px 14px;text-align:left;font-size:12px;font-weight:600;
                               color:#6E6E73;text-transform:uppercase;letter-spacing:0.5px;">Étape</th>
                    <th style="padding:10px 14px;text-align:left;font-size:12px;font-weight:600;
                               color:#6E6E73;text-transform:uppercase;letter-spacing:0.5px;">Statut</th>
                    <th style="padding:10px 14px;text-align:left;font-size:12px;font-weight:600;
                               color:#6E6E73;text-transform:uppercase;letter-spacing:0.5px;">Message</th>
                </tr>
            </thead>
            <tbody>{rows_html}
            </tbody>
        </table>
    """
    send_email(subject, recipients, _base(content))
