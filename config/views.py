from django.shortcuts import render
from django.http import HttpResponseServerError
from django.template.loader import get_template


def handler403(request, exception=None):
    return render(request, '403.html', status=403)


def handler404(request, exception=None):
    return render(request, '404.html', {'request_path': request.path}, status=404)


def handler500(request):
    try:
        template = get_template('500.html')
        return HttpResponseServerError(template.render(request=request))
    except Exception:
        return HttpResponseServerError('<h1>Erreur serveur</h1>', content_type='text/html')
