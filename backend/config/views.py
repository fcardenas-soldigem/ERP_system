from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Compra
from .serializers import CompraSerializer

def example_view(request):
    return JsonResponse({'message': 'Hello, world!'})

class ComprasListView(APIView):
    def get(self, request):
        compras = Compra.objects.all()
        serializer = CompraSerializer(compras, many=True)
        return Response(serializer.data)
