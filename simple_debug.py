from django.http import HttpResponse
from django.conf import settings

def simple_debug(request):
    import os
    from kullanici.models import CustomUser
    
    try:
        html = '<h1>Debug Info</h1>'
        html += '<p>DATABASE_URL: {}</p>'.format(os.environ.get('DATABASE_URL', 'NOT SET'))
        html += '<p>DB Engine: {}</p>'.format(settings.DATABASES['default']['ENGINE'])
        html += '<p>DB Name: {}</p>'.format(settings.DATABASES['default']['NAME'])
        html += '<p>Total users: {}</p>'.format(CustomUser.objects.count())
        html += '<h2>Users:</h2><ul>'
        
        for user in CustomUser.objects.all():
            html += '<li>User: {} (ID: {})</li>'.format(user.username, user.id)
        
        html += '</ul>'
        return HttpResponse(html)
    except Exception as e:
        return HttpResponse('<h1>Error: {}</h1>'.format(str(e)))
