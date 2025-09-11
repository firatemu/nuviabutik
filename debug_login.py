from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_login_view(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('kullanici_adi', '')
            password = request.POST.get('sifre', '')
            
            html = '<h1>Login Debug</h1>'
            html += '<p>Username: {}</p>'.format(username)
            html += '<p>Password length: {}</p>'.format(len(password))
            
            user = authenticate(request, username=username, password=password)
            
            if user:
                html += '<p>Authentication: SUCCESS</p>'
                html += '<p>User: {} (ID: {})</p>'.format(user.username, user.id)
                html += '<p>Is active: {}</p>'.format(user.is_active)
            else:
                html += '<p>Authentication: FAILED</p>'
                
            return HttpResponse(html)
            
        except Exception as e:
            return HttpResponse('<h1>Error: {}</h1>'.format(str(e)))
    else:
        return HttpResponse('<h1>Use POST method</h1>')
