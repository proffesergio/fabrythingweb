from core.helpers import CommonListAPIMixin, CustomPageNumberPagination, absolutize_image_list, createParsedCreatedAtUpdatedAt, isPlatformScope, renderResponse
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
    image=serializers.SerializerMethodField()

    class Meta:
        model = Categories
        fields = '__all__'

    def get_children(self, obj):
        children = Categories.objects.filter(parent_id=obj.id)
        return CategorySerializer(children, many=True, context=self.context).data

    def get_image(self, obj):
        # BUG 1: same relative-/api/media-path problem as ProductSerializer.get_image.
        return absolutize_image_list(obj.image, self.context.get('request'))

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
        if isPlatformScope(self.request.user):
            queryset = Categories.objects.filter(parent_id__isnull=True)
        else:
            queryset = Categories.objects.filter(parent_id__isnull=True, domain_user_id=self.request.user.domain_user_id_id)
        return queryset

    @CommonListAPIMixin.common_list_decorator(CategorySerializer)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)