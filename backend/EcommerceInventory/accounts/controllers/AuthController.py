from core.permission import IsSuperAdmin
from core.helpers import renderResponse
from accounts.models import Users
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate

# SignupAPIView used to live here: a public, unauthenticated endpoint that
# called Users.objects.create_user() with no role argument, so it minted an
# "Admin" (the model's old default) for anyone who posted to it -- and it
# trusted a client-supplied `domain_user_id` straight off the request body,
# so the new admin could attach itself to any tenant. It has been removed
# entirely rather than gated: nothing legitimate called /api/auth/signup/
# (the storefront customer signup is the separate, still-public
# /api/store/auth/signup/ -> storefront.views.CustomerSignupView, which
# always hardcodes role='Customer'). Back-office accounts are now only
# created by a logged-in platform staff member via
# UserController.CreateUserView (accounts/users/create/).


class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if username is None or password is None:
            return renderResponse(data='Please provide both username and password',message='Please provide both username and password',status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            access =refresh.access_token
            access['username'] = user.username
            access['email'] = user.email
            access['role'] = user.role
            access['profile_pic'] = user.profile_pic

            return Response({
                'refresh': str(refresh),
                'access': str(access),
                'message': 'Login Successful'
            })
        else:
            return renderResponse(data='Invalid credentials',message='Invalid credentials',status=status.HTTP_400_BAD_REQUEST)
    def get(self,request):
        return renderResponse(data='Please Use Post Method to Login',message='Please Use Post Method to Login',status=status.HTTP_400_BAD_REQUEST)
    
class PublicAPIView(APIView):
    def get(self, request):
        return renderResponse(data='This is a publicly accessible API',message='This is a publicly accessible API',status=status.HTTP_400_BAD_REQUEST)

class ProtectedAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return renderResponse(data='This is a protected API. You can access this because you are authenticated.',message='This is a protected API. You can access this because you are authenticated.',status=status.HTTP_400_BAD_REQUEST)

class SuperAdminCheckApi(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated,IsSuperAdmin]

    def get(self, request):
        return renderResponse(data='This is a Super Admin API. You can access this because you are authenticated.',message='This is a protected API. You can access this because you are authenticated.',status=status.HTTP_400_BAD_REQUEST)
