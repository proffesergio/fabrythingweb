from django.db.models import Avg
from rest_framework import serializers

from accounts.models import UserShippingAddress, Users
from catalog.models import Categories, ProductQuestions, ProductReviews, Products, ProductVariant
from orders.models import Order, OrderItem, OrderStatusLog


# ─── Catalog ────────────────────────────────────────────────────────────────


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
        child_ids = list(Categories.objects.filter(parent_id=obj.id).values_list('id', flat=True))
        return Products.objects.filter(
            category_id__in=[obj.id] + child_ids, status='ACTIVE',
        ).count()


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'size', 'color', 'price', 'discount_price',
                  'effective_price', 'stock_quantity', 'in_stock']


class StorefrontProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Products
        fields = [
            'id', 'name', 'slug', 'image', 'description',
            'initial_selling_price', 'discount_price',
            'color', 'brand', 'gender', 'available_sizes', 'material',
            'category_id', 'category_name',
            'average_rating', 'review_count', 'discount_percentage',
            'total_stock', 'created_at',
        ]

    def get_category_name(self, obj):
        return obj.category_id.name if obj.category_id else None

    def get_average_rating(self, obj):
        result = ProductReviews.objects.filter(product_id=obj.id, status='ACTIVE').aggregate(avg=Avg('rating'))
        return round(result['avg'], 1) if result['avg'] else 0

    def get_review_count(self, obj):
        return ProductReviews.objects.filter(product_id=obj.id, status='ACTIVE').count()

    def get_discount_percentage(self, obj):
        if obj.discount_price and obj.initial_selling_price and obj.initial_selling_price > 0:
            return round(((obj.initial_selling_price - obj.discount_price) / obj.initial_selling_price) * 100)
        return 0


class StorefrontProductDetailSerializer(StorefrontProductListSerializer):
    reviews = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    rating_distribution = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

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
            'total_stock', 'variants',
            'rating_distribution', 'reviews', 'questions',
            'created_at',
        ]

    def get_variants(self, obj):
        variants = obj.variants.filter(is_active=True).order_by('id')
        return ProductVariantSerializer(variants, many=True).data

    def get_reviews(self, obj):
        reviews = ProductReviews.objects.filter(product_id=obj.id, status='ACTIVE').order_by('-created_at')[:5]
        return StorefrontReviewSerializer(reviews, many=True).data

    def get_questions(self, obj):
        questions = ProductQuestions.objects.filter(product_id=obj.id, status='ACTIVE').order_by('-created_at')[:5]
        return StorefrontQuestionSerializer(questions, many=True).data

    def get_rating_distribution(self, obj):
        reviews = ProductReviews.objects.filter(product_id=obj.id, status='ACTIVE')
        total = reviews.count()
        if total == 0:
            return {str(i): 0 for i in range(1, 6)}
        return {
            str(star): round((reviews.filter(rating__gte=star, rating__lt=star + 1).count() / total) * 100)
            for star in range(1, 6)
        }


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


# ─── Account ──────────────────────────────────────────────────────────────


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


# ─── Cart (guest -> user sync) ───────────────────────────────────────────────


class CartLineInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CartMergeSerializer(serializers.Serializer):
    items = CartLineInputSerializer(many=True)


class CartItemSerializer(serializers.Serializer):
    """Read serializer for a persisted cart line, resolved against the variant."""
    variant_id = serializers.IntegerField(source='variant.id')
    product_id = serializers.IntegerField(source='variant.product_id')
    product_name = serializers.CharField(source='variant.product.name')
    product_slug = serializers.CharField(source='variant.product.slug')
    sku = serializers.CharField(source='variant.sku')
    size = serializers.CharField(source='variant.size')
    color = serializers.CharField(source='variant.color')
    unit_price = serializers.DecimalField(source='variant.effective_price', max_digits=10, decimal_places=2)
    stock_quantity = serializers.IntegerField(source='variant.stock_quantity')
    quantity = serializers.IntegerField()


# ─── COD Orders ─────────────────────────────────────────────────────────────


class PlaceOrderItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    """COD-only checkout payload."""
    items = PlaceOrderItemSerializer(many=True)
    shipping_address_id = serializers.IntegerField()
    contact_name = serializers.CharField(max_length=120)
    contact_phone = serializers.CharField(max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    # Honeypot: real users never fill this hidden field. Bots do.
    website = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_contact_phone(self, value):
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) < 6:
            raise serializers.ValidationError("Enter a valid phone number.")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Your cart is empty.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_slug', 'product_image', 'sku',
                  'size', 'color', 'unit_price', 'quantity', 'line_total']

    def get_product_slug(self, obj):
        return obj.variant.product.slug if obj.variant and obj.variant.product else None

    def get_product_image(self, obj):
        if obj.variant and obj.variant.product and obj.variant.product.image:
            images = obj.variant.product.image
            return images[0] if isinstance(images, list) and images else None
        return None


class OrderStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusLog
        fields = ['from_status', 'to_status', 'reason', 'created_at']


class CustomerOrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'status_display', 'payment_method',
                  'subtotal', 'shipping_amount', 'total_amount', 'currency',
                  'item_count', 'created_at']

    def get_item_count(self, obj):
        return obj.items.count()


class CustomerOrderDetailSerializer(CustomerOrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'status_display', 'payment_method',
                  'subtotal', 'shipping_amount', 'total_amount', 'currency',
                  'contact_name', 'contact_phone', 'shipping_address', 'notes',
                  'canceled_reason', 'items', 'status_logs', 'created_at']
