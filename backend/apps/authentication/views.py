from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer
from apps.empresas.models import Empresa
import traceback
from rest_framework import generics

User = get_user_model()

class LoginView(APIView):
    """
    Vista para manejar el inicio de sesión de usuarios.
    """

    permission_classes = [AllowAny]  # Permite acceso sin autenticación

    def post(self, request):
        try:
            print("Datos recibidos:", request.data)
            serializer = LoginSerializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                password = serializer.validated_data['password']
                
                print(f"Intentando autenticar usuario: {email}")
                user = authenticate(email=email, password=password)
                
                if user is not None:
                    # Verificar si el usuario tiene una empresa asignada
                    if not user.empresa:
                        # Asignar la primera empresa disponible (o según tu lógica de negocio)
                        empresa = Empresa.objects.first()
                        if empresa:
                            user.empresa = empresa
                            user.save()
                        else:
                            return Response(
                                {'error': 'No hay empresas disponibles en el sistema'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    
                    print(f"Usuario autenticado: {user.email}, Empresa: {user.empresa}")
                    refresh = RefreshToken.for_user(user)
                    user_serializer = UserSerializer(user)
                    
                    return Response({
                        'token': str(refresh.access_token),
                        'user': user_serializer.data
                    })
                else:
                    return Response(
                        {'error': 'Credenciales inválidas'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print("Error detallado:", e)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        try:
            print(f'Obteniendo perfil para usuario: {request.user.username}')
            print(f'Empresa asignada: {request.user.empresa.nombre if request.user.empresa else "No tiene empresa"}')
            
            user = self.get_object()
            serializer = self.get_serializer(user)
            data = serializer.data
            
            # Agregar información adicional
            data['has_empresa'] = bool(user.empresa)
            if user.empresa:
                data['empresa_status'] = {
                    'is_active': user.empresa.is_active,
                    'created_at': user.empresa.created_at.isoformat() if hasattr(user.empresa, 'created_at') else None,
                }
            
            print('Datos del perfil:', data)
            return Response(data)
        except Exception as e:
            print(f'Error al obtener perfil: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
