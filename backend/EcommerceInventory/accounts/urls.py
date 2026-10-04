from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .controllers import AuthController,UserController

urlpatterns = [
    path('login/',AuthController.LoginAPIView.as_view(),name='login'),
    # Silent session renewal for the admin panel and apps: POST {refresh}
    # returns a fresh access token (rotated refresh per SIMPLE_JWT settings).
    # Must stay public (see PUBLIC_API_PREFIXES) — by definition the caller
    # has no valid access token at this point.
    path('refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    # No public signup route here on purpose -- see the comment in
    # AuthController.py. Back-office accounts are created via users/create/
    # below, by an already-logged-in platform staff member only.
    path('publicApi/',AuthController.PublicAPIView.as_view(),name='publicapi'),
    path('protectedApi/',AuthController.ProtectedAPIView.as_view(),name='protectedapi'),
    path('superadminurl/',AuthController.SuperAdminCheckApi.as_view(),name='superadminurl'),
    path('users/',UserController.UserListView.as_view(),name='user_list'),
    path('users/create/',UserController.CreateUserView.as_view(),name='create_user'),
    path('userlist/',UserController.UserWithFilterListView.as_view(),name='user_list_filter'),
    path('updateuser/<pk>/',UserController.UpdateUsers.as_view(),name='update_user'),
    path('userpermission/<pk>/',UserController.UserPermissionsView.as_view(),name='user_permission'),
]
