class PrintRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(request.path)
        print(request.method)
        print(request.body)
        response = self.get_response(request)
        print(response.content)
        return response
