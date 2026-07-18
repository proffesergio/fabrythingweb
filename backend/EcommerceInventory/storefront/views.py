from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import generics
from rest_framework import status as http_status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserShippingAddress, Users
from catalog.models import Categories, ProductQuestions, ProductReviews, Products, ProductVariant
from core.helpers import CommonListAPIMixin, CustomPageNumberPagination, renderResponse
from core.models import StoreConfiguration
from orders.models import Order, OrderItem
from orders.services import place_cod_order

from .models import Cart, CartItem
from .serializers import (
    CartItemSerializer,
    CartMergeSerializer,
    CustomerOrderDetailSerializer,
    CustomerOrderListSerializer,
    CustomerProfileSerializer,
    PlaceOrderSerializer,
    ShippingAddressSerializer,
    StorefrontCategorySerializer,
    StorefrontProductDetailSerializer,
    StorefrontProductListSerializer,
    StorefrontReviewSerializer,
)


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access['username'] = user.username
    access['role'] = user.role
    return {'access': str(access), 'refresh': str(refresh)}


# ─── Store config (public) ───────────────────────────────────────────────────


class StoreConfigView(APIView):
    """Public store settings so the frontend renders the authoritative shipping rate."""
    permission_classes = [AllowAny]

    def get(self, request):
        cfg = StoreConfiguration.get_solo()
        return renderResponse(
            data={
                'store_name': cfg.store_name,
                'currency': cfg.currency,
                'cod_enabled': cfg.cod_enabled,
                'fixed_shipping_rate': float(cfg.fixed_shipping_rate),
                'free_shipping_threshold': (
                    float(cfg.free_shipping_threshold) if cfg.free_shipping_threshold is not None else None
                ),
                'support_phone': cfg.support_phone,
            },
            message='Store configuration',
        )


# ─── Public catalog ──────────────────────────────────────────────────────────


class PublicCategoryListView(generics.ListAPIView):
    serializer_class = StorefrontCategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Categories.objects.filter(parent_id__isnull=True).order_by('display_order')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return renderResponse(data=serializer.data, message='Categories retrieved successfully')


class PublicProductListView(generics.ListAPIView):
    serializer_class = StorefrontProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination
    authentication_classes = []

    def get_queryset(self):
        queryset = Products.objects.filter(status='ACTIVE')
        params = self.request.query_params

        category_slug = params.get('category')
        if category_slug:
            category = Categories.objects.filter(slug=category_slug).first()
            if category:
                category_ids = [category.id] + list(
                    Categories.objects.filter(parent_id=category.id).values_list('id', flat=True)
                )
                queryset = queryset.filter(category_id__in=category_ids)

        gender = params.get('gender')
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        price_min = params.get('price_min')
        price_max = params.get('price_max')
        if price_min:
            queryset = queryset.filter(
                Q(discount_price__gte=price_min) | Q(discount_price__isnull=True, initial_selling_price__gte=price_min)
            )
        if price_max:
            queryset = queryset.filter(
                Q(discount_price__lte=price_max) | Q(discount_price__isnull=True, initial_selling_price__lte=price_max)
            )

        for field in ('color', 'material', 'brand'):
            val = params.get(field)
            if val:
                queryset = queryset.filter(**{f'{field}__icontains': val})

        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search) |
                Q(brand__icontains=search) | Q(material__icontains=search) | Q(color__icontains=search)
            )

        ordering = params.get('ordering', '-created_at')
        valid_orderings = {
            'price_low': 'initial_selling_price',
            'price_high': '-initial_selling_price',
            'newest': '-created_at',
            'name': 'name',
        }
        return queryset.order_by(valid_orderings.get(ordering, ordering))

    @CommonListAPIMixin.common_list_decorator(StorefrontProductListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PublicProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = Products.objects.filter(slug=slug, status='ACTIVE').first()
        if not product:
            return renderResponse(data='Product not found', message='Product not found', status=404)

        data = StorefrontProductDetailSerializer(product).data
        if product.category_id:
            related = Products.objects.filter(
                category_id=product.category_id, status='ACTIVE'
            ).exclude(id=product.id)[:8]
            data['related_products'] = StorefrontProductListSerializer(related, many=True).data
        else:
            data['related_products'] = []
        return renderResponse(data=data, message='Product retrieved successfully')


class PublicHomepageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Categories.objects.filter(parent_id__isnull=True).order_by('display_order')[:8]
        new_arrivals = Products.objects.filter(status='ACTIVE').order_by('-created_at')[:8]
        on_sale = Products.objects.filter(status='ACTIVE', discount_price__isnull=False).order_by('-created_at')[:8]

        best_rated_ids = list(
            ProductReviews.objects.filter(status='ACTIVE')
            .values('product_id').annotate(avg_rating=Avg('rating'))
            .order_by('-avg_rating')[:8].values_list('product_id', flat=True)
        )
        best_rated = (
            Products.objects.filter(id__in=best_rated_ids, status='ACTIVE')
            if best_rated_ids else Products.objects.filter(status='ACTIVE')[:8]
        )

        all_discounted = list(Products.objects.filter(
            status='ACTIVE', discount_price__isnull=False, initial_selling_price__gt=0,
        ).select_related('category_id'))
        flash_sale = sorted(
            all_discounted,
            key=lambda p: (p.initial_selling_price - p.discount_price) / p.initial_selling_price,
            reverse=True,
        )[:8]

        now = timezone.now()
        days_until_sunday = (6 - now.weekday()) % 7 or 7
        flash_sale_end = (now + timedelta(days=days_until_sunday)).replace(hour=23, minute=59, second=59, microsecond=0)

        # Trending / best sellers now come from the COD Order layer.
        thirty_days_ago = now - timedelta(days=30)
        trending_ids = list(
            OrderItem.objects.filter(order__created_at__gte=thirty_days_ago)
            .exclude(order__status=Order.Status.CANCELED)
            .values('variant__product_id').annotate(c=Count('id')).order_by('-c')[:8]
            .values_list('variant__product_id', flat=True)
        )
        trending = (
            Products.objects.filter(id__in=trending_ids, status='ACTIVE')
            if trending_ids else Products.objects.filter(status='ACTIVE')[:8]
        )

        best_seller_ids = list(
            OrderItem.objects.exclude(order__status=Order.Status.CANCELED)
            .values('variant__product_id').annotate(total=Sum('quantity')).order_by('-total')[:8]
            .values_list('variant__product_id', flat=True)
        )
        best_sellers = (
            Products.objects.filter(id__in=best_seller_ids, status='ACTIVE')
            if best_seller_ids else Products.objects.filter(status='ACTIVE')[:8]
        )

        data = {
            'categories': StorefrontCategorySerializer(categories, many=True).data,
            'new_arrivals': StorefrontProductListSerializer(new_arrivals, many=True).data,
            'on_sale': StorefrontProductListSerializer(on_sale, many=True).data,
            'best_rated': StorefrontProductListSerializer(best_rated, many=True).data,
            'flash_sale': StorefrontProductListSerializer(flash_sale, many=True).data,
            'flash_sale_end': flash_sale_end.isoformat(),
            'trending': StorefrontProductListSerializer(trending, many=True).data,
            'best_sellers': StorefrontProductListSerializer(best_sellers, many=True).data,
        }
        return renderResponse(data=data, message='Homepage data retrieved successfully')


# ─── Customer auth ────────────────────────────────────────────────────────────


class CustomerSignupView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if not username or not email or not password:
            return renderResponse(data='Username, email, and password are required', message='Validation error', status=400)
        if Users.objects.filter(email=email).exists():
            return renderResponse(data='Email already exists', message='Email already exists', status=400)
        if Users.objects.filter(username=username).exists():
            return renderResponse(data='Username already exists', message='Username already exists', status=400)

        user = Users.objects.create_user(
            username=username, email=email, password=password,
            first_name=request.data.get('first_name', ''), last_name=request.data.get('last_name', ''),
            phone=request.data.get('phone', ''), role='Customer',
            country='Bangladesh', currency='BDT', time_zone='UTC+06:00',
        )
        tokens = issue_tokens(user)
        return Response({**tokens, 'message': 'Account created successfully'}, status=http_status.HTTP_201_CREATED)


class CustomerLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        from django.contrib.auth import authenticate

        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return renderResponse(data='Username and password are required', message='Validation error', status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            return renderResponse(data='Invalid credentials', message='Invalid credentials', status=400)

        return Response({**issue_tokens(user), 'message': 'Login successful'})


# ─── Customer account ─────────────────────────────────────────────────────────


class CustomerProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return renderResponse(data=CustomerProfileSerializer(request.user).data, message='Profile retrieved')

    def put(self, request):
        serializer = CustomerProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return renderResponse(data=serializer.data, message='Profile updated')
        return renderResponse(data=serializer.errors, message='Validation error', status=400)


class ShippingAddressListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = UserShippingAddress.objects.filter(user=request.user)
        return renderResponse(data=ShippingAddressSerializer(addresses, many=True).data, message='Addresses retrieved')

    def post(self, request):
        serializer = ShippingAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return renderResponse(data=serializer.data, message='Address added', status=201)
        return renderResponse(data=serializer.errors, message='Validation error', status=400)


class ShippingAddressDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        return UserShippingAddress.objects.filter(user=request.user, pk=pk).first()

    def put(self, request, pk):
        address = self._get(request, pk)
        if not address:
            return renderResponse(data='Address not found', message='Not found', status=404)
        serializer = ShippingAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return renderResponse(data=serializer.data, message='Address updated')
        return renderResponse(data=serializer.errors, message='Validation error', status=400)

    def delete(self, request, pk):
        address = self._get(request, pk)
        if not address:
            return renderResponse(data='Address not found', message='Not found', status=404)
        address.delete()
        return renderResponse(data=None, message='Address deleted')


# ─── Cart (guest -> user sync) ────────────────────────────────────────────────


class CartView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related('variant', 'variant__product').all()
        return renderResponse(data=CartItemSerializer(items, many=True).data, message='Cart retrieved')


class CartMergeView(APIView):
    """Union a guest's localStorage cart into the user's server cart on login."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartMergeSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        with transaction.atomic():
            for line in serializer.validated_data['items']:
                variant = ProductVariant.objects.filter(pk=line['variant_id'], is_active=True).first()
                if not variant:
                    continue
                item, created = CartItem.objects.get_or_create(
                    cart=cart, variant=variant, defaults={'quantity': line['quantity']},
                )
                if not created:
                    item.quantity += line['quantity']
                    item.save(update_fields=['quantity', 'updated_at'])

        items = cart.items.select_related('variant', 'variant__product').all()
        return renderResponse(data=CartItemSerializer(items, many=True).data, message='Cart merged')


# ─── COD Orders ───────────────────────────────────────────────────────────────


class PlaceOrderView(APIView):
    """Create a Cash-on-Delivery order — logged-in OR guest.

    Guests are allowed: they type an inline delivery address and the order is
    saved with customer=None (an anonymous COD order). Logged-in users may pass
    a saved address id instead. Throttled by user/IP + honeypot-protected.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    throttle_scope = 'orders.create'

    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        data = serializer.validated_data

        # Honeypot: a filled hidden field means a bot. Fail quietly (looks OK to the bot).
        if data.get('website'):
            return renderResponse(data={'order_number': 'ORD-PENDING'}, message='Order received', status=201)

        user = request.user if request.user.is_authenticated else None

        # Resolve the delivery address: a saved one (logged-in) or an inline one (guest).
        if user and data.get('shipping_address_id'):
            address = UserShippingAddress.objects.filter(user=user, pk=data['shipping_address_id']).first()
            if not address:
                return renderResponse(data='Shipping address not found', message='Invalid address', status=400)
            address_snapshot = {
                'address_type': address.address_type, 'address': address.address,
                'city': address.city, 'state': address.state,
                'pincode': address.pincode, 'country': address.country,
            }
        elif data.get('shipping_address'):
            inline = data['shipping_address']
            address_snapshot = {
                'address_type': inline.get('address_type', 'Home'),
                'address': inline['address'], 'city': inline['city'],
                'state': inline.get('state', ''), 'pincode': inline.get('pincode', ''),
                'country': inline.get('country', 'Bangladesh'),
            }
        else:
            return renderResponse(data='A delivery address is required.', message='Invalid address', status=400)

        try:
            order = place_cod_order(
                customer=request.user,
                items=data['items'],
                contact_name=data['contact_name'],
                contact_phone=data['contact_phone'],
                shipping_address=address_snapshot,
                notes=data.get('notes', ''),
                client_ip=get_client_ip(request),
            )
        except ValidationError as exc:
            detail = exc.detail
            messages = detail if isinstance(detail, list) else [str(detail)]
            return renderResponse(
                data=[str(m) for m in messages],
                message='Could not place order',
                status=getattr(exc, 'status_code', 400),
            )

        # Clear the server cart now that the order is placed (logged-in users only).
        if user:
            CartItem.objects.filter(cart__user=user).delete()

        return renderResponse(
            data={
                'order_id': order.id, 'order_number': order.order_number,
                'subtotal': float(order.subtotal), 'shipping_amount': float(order.shipping_amount),
                'total_amount': float(order.total_amount), 'currency': order.currency,
                'status': order.status,
            },
            message='Order placed successfully', status=201,
        )


class CustomerOrderListView(generics.ListAPIView):
    serializer_class = CustomerOrderListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

    @CommonListAPIMixin.common_list_decorator(CustomerOrderListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CustomerOrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = Order.objects.filter(customer=request.user, pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)
        return renderResponse(data=CustomerOrderDetailSerializer(order).data, message='Order retrieved')


class CustomerOrderCancelView(APIView):
    """A customer may cancel their own order while it is still cancelable."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = Order.objects.filter(customer=request.user, pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)
        if not order.can_transition_to(Order.Status.CANCELED):
            return renderResponse(data='This order can no longer be canceled', message='Not allowed', status=400)
        order.transition_to(Order.Status.CANCELED, changed_by=request.user, reason=request.data.get('reason', 'Canceled by customer'))
        return renderResponse(data={'status': order.status}, message='Order canceled')


# ─── Reviews & questions ──────────────────────────────────────────────────────


class CustomerReviewCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        rating = request.data.get('rating')
        if not product_id or rating is None:
            return renderResponse(data='product_id and rating are required', message='Validation error', status=400)
        product = Products.objects.filter(pk=product_id, status='ACTIVE').first()
        if not product:
            return renderResponse(data='Product not found', message='Not found', status=404)
        review = ProductReviews.objects.create(
            product_id=product, review_user_id=request.user, domain_user_id=product.domain_user_id,
            rating=float(rating), reviews=request.data.get('review', ''),
            review_images=request.data.get('review_images', []) or [], status='ACTIVE',
        )
        return renderResponse(data=StorefrontReviewSerializer(review).data, message='Review submitted', status=201)


class CustomerQuestionCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        question_text = request.data.get('question')
        if not product_id or not question_text:
            return renderResponse(data='product_id and question are required', message='Validation error', status=400)
        product = Products.objects.filter(pk=product_id, status='ACTIVE').first()
        if not product:
            return renderResponse(data='Product not found', message='Not found', status=404)
        question = ProductQuestions.objects.create(
            product_id=product, question_user_id=request.user, answer_user_id=request.user,
            domain_user_id=product.domain_user_id, question=question_text, answer='', status='ACTIVE',
        )
        return renderResponse(data={'id': question.id, 'question': question.question}, message='Question submitted', status=201)


# ─── Admin (COD order management) ─────────────────────────────────────────────


class AdminDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        orders = Order.objects.all()
        revenue_base = orders.exclude(status=Order.Status.CANCELED)

        data = {
            'orders': {
                'today': orders.filter(created_at__gte=today_start).count(),
                'this_month': orders.filter(created_at__gte=month_start).count(),
                'total': orders.count(),
            },
            'revenue': {
                'today': float(revenue_base.filter(created_at__gte=today_start).aggregate(t=Sum('total_amount'))['t'] or 0),
                'this_month': float(revenue_base.filter(created_at__gte=month_start).aggregate(t=Sum('total_amount'))['t'] or 0),
            },
            'status_distribution': {
                s.value: orders.filter(status=s.value).count() for s in Order.Status
            },
            'recent_orders': CustomerOrderListSerializer(orders.order_by('-created_at')[:10], many=True).data,
            'total_products': Products.objects.filter(status='ACTIVE').count(),
            'total_customers': Users.objects.filter(role='Customer').count(),
        }
        return renderResponse(data=data, message='Dashboard data retrieved')


class AdminOrderListView(generics.ListAPIView):
    serializer_class = CustomerOrderListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)
        return queryset

    @CommonListAPIMixin.common_list_decorator(CustomerOrderListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AdminOrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = Order.objects.filter(pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)
        data = CustomerOrderDetailSerializer(order).data
        data['allowed_transitions'] = list(order.ALLOWED_TRANSITIONS.get(order.status, set()))
        if order.customer:
            data['customer'] = {
                'id': order.customer.id, 'username': order.customer.username,
                'email': order.customer.email, 'phone': order.customer.phone,
            }
        return renderResponse(data=data, message='Order retrieved')

    def patch(self, request, pk):
        order = Order.objects.filter(pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)
        new_status = request.data.get('status')
        try:
            order.transition_to(new_status, changed_by=request.user, reason=request.data.get('reason', ''))
        except Exception as exc:
            return renderResponse(data=str(exc), message='Invalid transition', status=400)
        return renderResponse(
            data={'id': order.id, 'status': order.status, 'order_number': order.order_number},
            message=f'Order status updated to {order.status}',
        )
