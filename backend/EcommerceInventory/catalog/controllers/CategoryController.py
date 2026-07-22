from core.helpers import CommonListAPIMixin, CustomPageNumberPagination, createParsedCreatedAtUpdatedAt, renderResponse
from catalog.models import Categories
from rest_framework import generics
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from django.db import models

@createParsedCreatedAtUpdatedAt
class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    domain_user_id=serializers.SerializerMethodField()
    added_by_user_id=serializers.SerializerMethodField()
    parent_id=serializers.SerializerMethodField()

    class Meta:
        model = Categories
        fields = '__all__'

    def get_children(self, obj):
        children = Categories.objects.filter(parent_id=obj.id)
        return CategorySerializer(children, many=True).data

    def get_domain_user_id(self,obj):
        if not obj.domain_user_id:
            return None
        return "#"+str(obj.domain_user_id.id)+" "+obj.domain_user_id.username

    def get_added_by_user_id(self,obj):
        if not obj.added_by_user_id:
            return None
        return "#"+str(obj.added_by_user_id.id)+" "+obj.added_by_user_id.username
    
    def get_parent_id(self,obj):
        return "#"+str(obj.parent_id.id)+" "+obj.parent_id.name if obj.parent_id else None
class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        # Super Admin sees all categories; others see only their domain's categories
        if self.request.user.role == 'Super Admin' or self.request.user.domain_user_id_id == self.request.user.id:
            queryset = Categories.objects.filter(parent_id__isnull=True)
        else:
            queryset = Categories.objects.filter(parent_id__isnull=True, domain_user_id=self.request.user.domain_user_id_id)
        return queryset

    @CommonListAPIMixin.common_list_decorator(CategorySerializer)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)