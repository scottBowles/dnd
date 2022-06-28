from django.utils import timezone
from nucleus.models import User


class PrintRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("request.path")
        print(request.path)
        print("request.method")
        print(request.method)
        print("request.body")
        print(request.body)
        print("request.headers")
        print(request.headers)
        response = self.get_response(request)
        print("response.content")
        print(response.content)
        return response


class UpdateLastActivityMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            User.objects.filter(pk=request.user.id).update(last_activity=timezone.now())
        response = self.get_response(request)

        return response
