import importlib.util
import pathlib

mail_path = pathlib.Path(__file__).parent / "config" / "mail.py"
spec = importlib.util.spec_from_file_location("mail", mail_path)
mail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mail)

mail.send_email(
    subject="Test envoi mail",
    recipients=["a.ralantoharivelo@pamf.mg"],  # <-- changer ici
    html_body="<h1>Test</h1><p>L'envoi de mail fonctionne.</p>",
)
