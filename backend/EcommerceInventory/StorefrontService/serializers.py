from rest_framework import serializers
from django.db.models import Avg, Count
from ProductServices.models import Categories, Products, ProductReviews, ProductQuestions
from UserServices.models import Users, UserShippingAddress
from OrderService.models import SalesOrder, SalesOrderOrderItems


class StorefrontCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Categories
        fields = ['id', 'name', 'slug', 'image', 'description', 'display_order', 'children', 'product_count']

    def get_children(self, obj):
        children = Categories.objects.filter(parent_id=obj.id)
        return StorefrontCategorySerializer(children, many=True).data

    def get_product_count(self, obj):
        # Include products in this category AND all direct children
        child_ids = list(Categories.objects.filter(parent_id=obj.id).values_list('id', flat=True))
        return Products.objects.filter(
            category_id__in=[obj.id] + child_ids,
            status='ACTIVE',
        ).count()


class StorefrontProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Products
        fields = [
            'id', 'name', 'slug', 'image', 'description',
            'initial_selling_price', 'discount_price',
            'color', 'brand', 'gender', 'available_sizes', 'material',
            'category_id', 'category_name',
            'average_rating', 'review_count', 'discount_percentage',
            'created_at',
        ]

    def get_category_name(self, obj):
        return obj.category_id.name if obj.category_id else None

    def get_average_rating(self, obj):
        result = ProductReviews.objects.filter(
            product_id=obj.id, status='ACTIVE'
        ).aggregate(avg=Avg('rating'))
        return round(result['avg'], 1) if result['avg'] else 0

    def get_review_count(self, obj):
        return ProductReviews.objects.filter(
            product_id=obj.id, status='ACTIVE'
        ).count()

    def get_discount_percentage(self, obj):
        if obj.discount_price and obj.initial_selling_price and obj.initial_selling_price > 0:
            return round(
                ((obj.initial_selling_price - obj.discount_price) / obj.initial_selling_price) * 100
            )
        return 0


class StorefrontProductDetailSerializer(StorefrontProductListSerializer):
    reviews = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    rating_distribution = serializers.SerializerMethodField()

    class Meta:
        model = Products
        fields = [
            'id', 'name', 'slug', 'image', 'description', 'html_description',
            'specifications', 'highlights',
            'initial_selling_price', 'discount_price', 'tax_percentage',
            'color', 'brand', 'brand_model', 'gender',
            'available_sizes', 'size_chart', 'material',
            'seo_title', 'seo_description', 'seo_keywords',
            'category_id', 'category_name',
            'average_rating', 'review_count', 'discount_percentage',
            'rating_distribution', 'reviews', 'questions',
            'created_at',
        ]

    def get_reviews(self, obj):
        reviews = ProductReviews.objects.filter(
            product_id=obj.id, status='ACTIVE'
        ).order_by('-created_at')[:5]
        return StorefrontReviewSerializer(reviews, many=True).data

    def get_questions(self, obj):
        questions = ProductQuestions.objects.filter(
            product_id=obj.id, status='ACTIVE'
        ).order_by('-created_at')[:5]
        return StorefrontQuestionSerializer(questions, many=True).data

    def get_rating_distribution(self, obj):
        reviews = ProductReviews.objects.filter(product_id=obj.id, status='ACTIVE')
        total = reviews.count()
        if total == 0:
            return {str(i): 0 for i in range(1, 6)}
        distribution = {}
        for star in range(1, 6):
            count = reviews.filter(rating__gte=star, rating__lt=star + 1).count()
            distribution[str(star)] = round((count / total) * 100)
        return distribution


class StorefrontReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReviews
        fields = ['id', 'rating', 'reviews', 'review_images', 'reviewer_name', 'created_at']

    def get_reviewer_name(self, obj):
        if obj.review_user_id:
            return obj.review_user_id.first_name or obj.review_user_id.username
        return 'Anonymous'


class StorefrontQuestionSerializer(serializers.ModelSerializer):
    asked_by = serializers.SerializerMethodField()

    class Meta:
        model = ProductQuestions
        fields = ['id', 'question', 'answer', 'asked_by', 'created_at']

    def get_asked_by(self, obj):
        if obj.question_user_id:
            return obj.question_user_id.first_name or obj.question_user_id.username
        return 'Anonymous'


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserShippingAddress
        fields = ['id', 'address_type', 'address', 'city', 'state', 'pincode', 'country']
        read_only_fields = ['id']


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'profile_pic']
        read_only_fields = ['id', 'username', 'email']


class OrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    size = serializers.CharField(required=False, allow_blank=True)


class PlaceOrderSerializer(serializers.Serializer):
    shipping_address_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=['COD', 'BKASH'])
    items = OrderItemSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class SalesOrderItemDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    product_slug = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrderOrderItems
        fields = [
            'id', 'product_id', 'product_name', 'product_image', 'product_slug',
            'quantity_ordered', 'quantity_delivered', 'quantity_cancelled',
            'purchase_price', 'discount_amount', 'discount_type',
            'amount_ordered', 'tax_amount',
        ]

    def get_product_name(self, obj):
        return obj.product_id.name if obj.product_id else None

    def get_product_image(self, obj):
        if obj.product_id and obj.product_id.image:
            images = obj.product_id.image
            return images[0] if isinstance(images, list) and images else None
        return None

    def get_product_slug(self, obj):
        return obj.product_id.slug if obj.product_id else None


class CustomerOrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'so_code', 'so_date', 'status', 'payment_status',
            'payment_terms', 'shipping_amount', 'shipping_type',
            'item_count', 'total_amount', 'created_at',
        ]

    def get_item_count(self, obj):
        return SalesOrderOrderItems.objects.filter(so_id=obj.id).count()

    def get_total_amount(self, obj):
        items = SalesOrderOrderItems.objects.filter(so_id=obj.id)
        return float(sum(item.amount_ordered for item in items))


class CustomerOrderDetailSerializer(CustomerOrderListSerializer):
    items = serializers.SerializerMethodField()
    shipping_address = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'so_code', 'so_date', 'expected_delivery_date',
            'status', 'payment_status', 'payment_terms',
            'discount_amount', 'discount_type',
            'shipping_amount', 'shipping_type',
            'item_count', 'total_amount', 'items',
            'shipping_address', 'created_at',
        ]

    def get_items(self, obj):
        items = SalesOrderOrderItems.objects.filter(so_id=obj.id)
        return SalesOrderItemDetailSerializer(items, many=True).data

    def get_shipping_address(self, obj):
        if obj.additional_details and isinstance(obj.additional_details, dict):
            return obj.additional_details.get('shipping_address', None)
        return None
