from django.http.response import JsonResponse
from website.schema import schema


def introspection_schema(request):
    data = {"data": schema.introspect()}
    return JsonResponse(data)
