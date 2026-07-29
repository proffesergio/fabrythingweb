from core.helpers import CommonListAPIMixin, CommonListAPIMixinWithFilter, CustomPageNumberPagination, PLATFORM_STAFF_ROLES, createParsedCreatedAtUpdatedAt, executeQuery, renderResponse
from accounts.models import Modules, UserPermissions, Users
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers
from rest_framework import generics

# User management (list/edit accounts, grant module permissions) is a
# back-office function -- every view below was IsAuthenticated only, with no
# role check, so any authenticated Customer/Rider/Restaurant could reach it.
# UpdateUsers is the sharp edge: its serializer exposes `role`, and a
# self-signed-up Customer's domain_user_id_id == their own id (see
# core.helpers.isPlatformStaff docstring), so `PATCH /api/auth/updateuser/<own
# id>/` matched their own row through the existing domain filter and let them
# set their own role to "Super Admin" -- a self-service privilege escalation.
# PLATFORM_STAFF_ROLES (not the full isPlatformStaff predicate) is used here:
# these views already scope by the caller's own domain_user_id_id, so a
# legitimate non-root Staff/Admin sub-account must keep managing its own
# tenant's users -- only the role axis (is this a back-office account at all)
# needs gating, same reasoning as ProductListView/CategoryListView.

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=Users
        fields=['id','username','first_name','last_name','email','profile_pic']

@createParsedCreatedAtUpdatedAt
class UserSerializerWithFilters(serializers.ModelSerializer):
    date_joined=serializers.DateTimeField(format="%dth %B %Y, %H:%M", read_only=True)
    last_login=serializers.DateTimeField(format="%dth %B %Y, %H:%M", read_only=True)
    added_by_user_id=serializers.SerializerMethodField()
    domain_user_id=serializers.SerializerMethodField()
    class Meta:
        model=Users
        fields=['id', 'first_name', 'last_name', 'date_joined', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'country', 'profile_pic', 'account_status', 'role', 'dob', 'username', 'social_media_links', 'addition_details', 'language', 'departMent', 'designation', 'time_zone', 'last_login', 'last_device', 'last_ip', 'currency', 'domain_name', 'plan_type', 'created_at', 'updated_at', 'domain_user_id', 'added_by_user_id']

    def get_domain_user_id(self,obj):
        return "#"+str(obj.domain_user_id.id) +" "+obj.domain_user_id.username if obj.domain_user_id!=None else ''
    
    def get_added_by_user_id(self,obj):
        return "#"+str(obj.added_by_user_id.id) +" "+obj.added_by_user_id.username if obj.added_by_user_id!=None else ''

class UserListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        if request.user.role not in PLATFORM_STAFF_ROLES:
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        users=Users.objects.filter(domain_user_id=request.user.domain_user_id_id)
        serializer=UserSerializer(users,many=True)
        return renderResponse(data=serializer.data,message="All Users",status=200)

class UserWithFilterListView(generics.ListAPIView):
    serializer_class = UserSerializerWithFilters
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        if self.request.user.role not in PLATFORM_STAFF_ROLES:
            raise PermissionDenied('Staff account required.')
        queryset=Users.objects.filter(domain_user_id=self.request.user.domain_user_id_id)
        return queryset

    @CommonListAPIMixinWithFilter.common_list_decorator(UserSerializerWithFilters)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)


class UpdateUsers(generics.UpdateAPIView):
    serializer_class = UserSerializerWithFilters
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role not in PLATFORM_STAFF_ROLES:
            raise PermissionDenied('Staff account required.')
        return Users.objects.filter(domain_user_id=self.request.user.domain_user_id_id,id=self.kwargs['pk'])

    def perform_update(self,serializer):
        serializer.save()


class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request,pk):
        if request.user.role not in PLATFORM_STAFF_ROLES:
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        query='''
            SELECT 
                userservices_modules.module_name, 
                userservices_modules.id as module_id, 
                userservices_modules.parent_id_id, 
                COALESCE(userservices_userpermissions.is_permission,0) as is_permission,
                userservices_userpermissions.user_id, 
                userservices_userpermissions.domain_user_id_id 
                FROM
                    `userservices_modules` 
                    left join 
                        userservices_userpermissions
                    on 
                    userservices_userpermissions.module_id=userservices_modules.id and 
            userservices_userpermissions.user_id=%s;
        '''

        permissions=executeQuery(query,[pk])

        permissionList={}
        for permission in permissions:
            if permission['parent_id_id']==None:
                permission['children']=[]
                permissionList[permission['module_id']]=permission
            
        for permission in permissions:
            if permission['parent_id_id']!=None:
                permissionList[permission['parent_id_id']]['children'].append(permission)

        permissionList=permissionList.values()
        return renderResponse(data=permissionList,message="User Permissions",status=200)

    def post(self,request,pk):
        if request.user.role not in PLATFORM_STAFF_ROLES:
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        data=request.data
        for item in data:
            if 'id' in item and item['id']!=None:
                permission=UserPermissions.objects.get(id=item['id'])
                permission.is_permission=item['is_permission']
            else:
                module=Modules.objects.get(id=item['module_id'])
                permission=UserPermissions(module=module,user_id=pk,is_permission=item['is_permission'])

            permission.save()

            if 'children' in item:
                for child in item['children']:
                    if 'id' in child and child['id']!=None:
                        permission=UserPermissions.objects.get(id=child['id'])
                        permission.is_permission=child['is_permission']
                    else:
                        module=Modules.objects.get(id=child['module_id'])
                        permission=UserPermissions(module=module,user_id=pk,is_permission=child['is_permission'])

                        permission.save()
        return renderResponse(data=[],message="Permissions Updated",status=200)