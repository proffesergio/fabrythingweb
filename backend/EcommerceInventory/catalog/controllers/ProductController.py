from accounts.models import Users
from core.helpers import CommonListAPIMixin, CustomPageNumberPagination, absolutize_image_list, createParsedCreatedAtUpdatedAt, isPlatformScope, renderResponse
from catalog.models import ProductQuestions, ProductReviews, Products
from catalog.services_price_sync import sync_source_prices
from rest_framework import generics
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from django.db import models

@createParsedCreatedAtUpdatedAt
class ProductReviewSerializer(serializers.ModelSerializer):
    review_user_id=serializers.SerializerMethodField()
    class Meta:
        model=ProductReviews
        fields='__all__'
    
    def get_review_user_id(self,obj):
        return "#"+str(obj.review_user_id.id)+" "+obj.review_user_id.username

@createParsedCreatedAtUpdatedAt
class ProductQuestionSerializer(serializers.ModelSerializer):
    question_user_id=serializers.SerializerMethodField()
    answer_user_id=serializers.SerializerMethodField()
    class Meta:
        model=ProductQuestions
        fields='__all__'

    def get_question_user_id(self,obj):
        return "#"+str(obj.question_user_id.id)+" "+obj.question_user_id.username
    
    def get_answer_user_id(self,obj):
        return "#"+str(obj.answer_user_id.id)+" "+obj.answer_user_id.username
@createParsedCreatedAtUpdatedAt
class ProductSerializer(serializers.ModelSerializer):
    category_id=serializers.SerializerMethodField()
    domain_user_id=serializers.SerializerMethodField()
    added_by_user_id=serializers.SerializerMethodField()
    image=serializers.SerializerMethodField()
    class Meta:
        model = Products
        fields = '__all__'

    def get_image(self,obj):
        # BUG 1: Products.image can hold a relative /api/media/<sha256>/ path
        # (core.storage.save_file's DB-blob fallback) — absolutize it here too,
        # same as the storefront serializer, so the admin panel image previews
        # don't 404 either. See core.helpers.absolutize_media_url.
        return absolutize_image_list(obj.image, self.context.get('request'))

    def get_category_id(self,obj):
        return "#"+str(obj.category_id.id)+" "+obj.category_id.name
    
    def get_domain_user_id(self,obj):
        if not obj.domain_user_id:
            return None
        return "#"+str(obj.domain_user_id.id)+" "+obj.domain_user_id.username

    def get_added_by_user_id(self,obj):
        if not obj.added_by_user_id:
            return None
        return "#"+str(obj.added_by_user_id.id)+" "+obj.added_by_user_id.username


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        # Super Admin sees all products; others see only their domain's products
        if isPlatformScope(self.request.user):
            queryset = Products.objects.all()
        else:
            queryset = Products.objects.filter(domain_user_id=self.request.user.domain_user_id_id)
        return queryset
    
    @CommonListAPIMixin.common_list_decorator(ProductSerializer)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)


class ProductReviewListView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset=ProductReviews.objects.filter(domain_user_id=self.request.user.domain_user_id_id,product_id=self.kwargs['product_id'])
        return queryset
    
    @CommonListAPIMixin.common_list_decorator(ProductReviewSerializer)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)
    
class ProductQuestionsListView(generics.ListAPIView):
    serializer_class = ProductQuestionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset=ProductQuestions.objects.filter(domain_user_id=self.request.user.domain_user_id_id,product_id=self.kwargs['product_id'])
        return queryset
    
    @CommonListAPIMixin.common_list_decorator(ProductQuestionSerializer)
    def list(self,request,*args,**kwargs):
        return super().list(request,*args,**kwargs)


class CreateProductReviewView(generics.CreateAPIView):
    serializer_class = ProductReviewSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self,serializer):
        if self.request.data.get('review_user_id'):
            serializer.save(domain_user_id=self.request.user.domain_user_id,review_user_id=Users.objects.get(id=int(self.request.data.get('review_user_id'))),product_id=Products.objects.get(id=self.kwargs['product_id']))
        else:
            serializer.save(domain_user_id=self.request.user.domain_user_id,product_id=Products.objects.get(id=self.kwargs['product_id']),review_user_id=self.request.user)

class CreateProductQuestionsView(generics.CreateAPIView):
    serializer_class = ProductQuestionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self,serializer):
        if self.request.data.get('question_user_id') and self.request.data.get('answer_user_id'):
            serializer.save(domain_user_id=self.request.user.domain_user_id,question_user_id=Users.objects.get(id=int(self.request.data.get('question_user_id'))),answer_user_id=Users.objects.get(id=int(self.request.data.get('answer_user_id'))),product_id=Products.objects.get(id=self.kwargs['product_id']))
        else:
            serializer.save(domain_user_id=self.request.user.domain_user_id,product_id=Products.objects.get(id=self.kwargs['product_id']),question_user_id=self.request.user,answer_user_id=self.request.user)



class UpdateProductReviewView(generics.UpdateAPIView):
    serializer_class = ProductReviewSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductReviews.objects.filter(domain_user_id=self.request.user.domain_user_id_id,product_id=self.kwargs['product_id'],id=self.kwargs['pk'])

    def perform_update(self,serializer):
        serializer.save()


class AdminSyncPricesView(APIView):
    """Re-fetch partner-store (potakait.com / canvasit.com.bd) prices for
    every product carrying a source_url and mirror them onto our catalog.
    Platform-scope only (Super Admin or a domain-root user) -- everyone
    else, including ordinary Staff, is forbidden."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isPlatformScope(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        changes = sync_source_prices()
        return renderResponse(
            data={"changes": [c for c in changes if c["updated"]],
                  "checked": len(changes)},
            message='Prices synced')


class UpdateProductQuestionsView(generics.UpdateAPIView):
    serializer_class = ProductQuestionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductQuestions.objects.filter(domain_user_id=self.request.user.domain_user_id_id,product_id=self.kwargs['product_id'],id=self.kwargs['pk'])

    def perform_update(self,serializer):
        if self.request.data.get('answer'):
            if self.request.data.get('answer_user_id'):
                serializer.save(answer_user_id=Users.objects.get(id=int(self.request.data.get('answer_user_id'))))
            else:
                serializer.save(answer_user_id=self.request.user)
        else:
            serializer.save()
