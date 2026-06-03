import uuid
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from EcommerceInventory.Helpers import (
    CommonListAPIMixin,
    CustomPageNumberPagination,
    renderResponse,
)
from OrderService.models import SalesOrder, SalesOrderOrderItems
from ProductServices.models import (
    Categories,
    ProductQuestions,
    ProductReviews,
    Products,
)
from UserServices.models import UserShippingAddress, Users

from .serializers import (
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


# ─── Public endpoints (no auth) ────────────────────────────────────────────


class PublicCategoryListView(generics.ListAPIView):
    """Public category tree for storefront navigation."""
    serializer_class = StorefrontCategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Categories.objects.filter(parent_id__isnull=True).order_by('display_order')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return renderResponse(data=serializer.data, message='Categories retrieved successfully')


class PublicProductListView(generics.ListAPIView):
    """Public product listing with filters for the storefront catalog."""
    serializer_class = StorefrontProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination
    authentication_classes = []

    def get_queryset(self):
        queryset = Products.objects.filter(status='ACTIVE')
        params = self.request.query_params

        # Category filter (by slug or id)
        category_slug = params.get('category')
        if category_slug:
            category = Categories.objects.filter(slug=category_slug).first()
            if category:
                # Include child categories
                category_ids = [category.id]
                children = Categories.objects.filter(parent_id=category.id)
                category_ids.extend(children.values_list('id', flat=True))
                queryset = queryset.filter(category_id__in=category_ids)

        # Gender filter
        gender = params.get('gender')
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        # Price range
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

        # Color filter
        color = params.get('color')
        if color:
            queryset = queryset.filter(color__icontains=color)

        # Material filter
        material = params.get('material')
        if material:
            queryset = queryset.filter(material__icontains=material)

        # Brand filter
        brand = params.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # Search
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(brand__icontains=search) |
                Q(material__icontains=search) |
                Q(color__icontains=search)
            )

        # Sorting
        ordering = params.get('ordering', '-created_at')
        valid_orderings = {
            'price_low': 'initial_selling_price',
            'price_high': '-initial_selling_price',
            'newest': '-created_at',
            'name': 'name',
        }
        queryset = queryset.order_by(valid_orderings.get(ordering, ordering))

        return queryset

    @CommonListAPIMixin.common_list_decorator(StorefrontProductListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PublicProductDetailView(APIView):
    """Public product detail page with reviews, Q&A, and related products."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = Products.objects.filter(slug=slug, status='ACTIVE').first()
        if not product:
            return renderResponse(data='Product not found', message='Product not found', status=404)

        serializer = StorefrontProductDetailSerializer(product)
        data = serializer.data

        # Related products (same category, exclude current)
        if product.category_id:
            related = Products.objects.filter(
                category_id=product.category_id, status='ACTIVE'
            ).exclude(id=product.id)[:8]
            data['related_products'] = StorefrontProductListSerializer(related, many=True).data
        else:
            data['related_products'] = []

        return renderResponse(data=data, message='Product retrieved successfully')


class PublicHomepageView(APIView):
    """Homepage data: featured products, new arrivals, categories, flash sale, trending."""
    permission_classes = [AllowAny]

    def get(self, request):
        # Top-level categories
        categories = Categories.objects.filter(
            parent_id__isnull=True
        ).order_by('display_order')[:8]

        # New arrivals (latest 8 active products)
        new_arrivals = Products.objects.filter(
            status='ACTIVE'
        ).order_by('-created_at')[:8]

        # On sale (products with discount)
        on_sale = Products.objects.filter(
            status='ACTIVE', discount_price__isnull=False
        ).order_by('-created_at')[:8]

        # Best rated — evaluate subquery to a list to avoid MySQL LIMIT-in-subquery error
        best_rated_ids = list(ProductReviews.objects.filter(
            status='ACTIVE'
        ).values('product_id').annotate(
            avg_rating=Avg('rating')
        ).order_by('-avg_rating')[:8].values_list('product_id', flat=True))
        if best_rated_ids:
            best_rated = Products.objects.filter(id__in=best_rated_ids, status='ACTIVE')
        else:
            best_rated = Products.objects.filter(status='ACTIVE').order_by('?')[:8]

        # Flash sale: products with highest discount percentage
        all_discounted = list(Products.objects.filter(
            status='ACTIVE', discount_price__isnull=False,
            initial_selling_price__gt=0
        ).select_related('category_id'))
        flash_sale = sorted(
            all_discounted,
            key=lambda p: (p.initial_selling_price - p.discount_price) / p.initial_selling_price,
            reverse=True
        )[:8]

        # Flash sale end: next Sunday midnight BD time
        now = timezone.now()
        days_until_sunday = (6 - now.weekday()) % 7 or 7
        flash_sale_end = (now + timedelta(days=days_until_sunday)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )

        # Trending: most ordered in last 30 days — evaluate to list first
        thirty_days_ago = now - timedelta(days=30)
        trending_ids = list(SalesOrderOrderItems.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('product_id').annotate(
            order_count=Count('id')
        ).order_by('-order_count')[:8].values_list('product_id', flat=True))
        if trending_ids:
            trending = Products.objects.filter(id__in=trending_ids, status='ACTIVE')
        else:
            trending = Products.objects.filter(status='ACTIVE').order_by('?')[:8]

        # Best sellers: most total quantity sold — evaluate to list first
        best_seller_ids = list(SalesOrderOrderItems.objects.values('product_id').annotate(
            total_sold=Sum('quantity_ordered')
        ).order_by('-total_sold')[:8].values_list('product_id', flat=True))
        if best_seller_ids:
            best_sellers = Products.objects.filter(id__in=best_seller_ids, status='ACTIVE')
        else:
            best_sellers = Products.objects.filter(status='ACTIVE').order_by('?')[:8]

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


# ─── Customer Auth ──────────────────────────────────────────────────────────


class CustomerSignupView(APIView):
    """Customer registration — sets role to Customer."""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        phone = request.data.get('phone', '')

        if not username or not email or not password:
            return renderResponse(
                data='Username, email, and password are required',
                message='Validation error',
                status=400,
            )

        if Users.objects.filter(email=email).exists():
            return renderResponse(data='Email already exists', message='Email already exists', status=400)

        if Users.objects.filter(username=username).exists():
            return renderResponse(data='Username already exists', message='Username already exists', status=400)

        user = Users.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='Customer',
            country='Bangladesh',
            currency='BDT',
            time_zone='UTC+06:00',
        )
        user.save()

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access['username'] = user.username
        access['email'] = user.email
        access['role'] = user.role
        access['profile_pic'] = user.profile_pic

        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'message': 'Account created successfully',
        }, status=status.HTTP_201_CREATED)


class CustomerLoginView(APIView):
    """Customer login — includes role in token."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return renderResponse(
                data='Username and password are required',
                message='Validation error',
                status=400,
            )

        user = authenticate(request, username=username, password=password)
        if not user:
            return renderResponse(data='Invalid credentials', message='Invalid credentials', status=400)

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access['username'] = user.username
        access['email'] = user.email
        access['role'] = user.role
        access['profile_pic'] = user.profile_pic

        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'message': 'Login successful',
        })


# ─── Customer Account (auth required) ──────────────────────────────────────


class CustomerProfileView(APIView):
    """Get or update customer profile."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomerProfileSerializer(request.user)
        return renderResponse(data=serializer.data, message='Profile retrieved')

    def put(self, request):
        serializer = CustomerProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return renderResponse(data=serializer.data, message='Profile updated')
        return renderResponse(data=serializer.errors, message='Validation error', status=400)


class ShippingAddressListCreateView(APIView):
    """List and create shipping addresses."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = UserShippingAddress.objects.filter(user=request.user)
        serializer = ShippingAddressSerializer(addresses, many=True)
        return renderResponse(data=serializer.data, message='Addresses retrieved')

    def post(self, request):
        serializer = ShippingAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return renderResponse(data=serializer.data, message='Address added', status=201)
        return renderResponse(data=serializer.errors, message='Validation error', status=400)


class ShippingAddressDetailView(APIView):
    """Update or delete a shipping address."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_address(self, request, pk):
        return UserShippingAddress.objects.filter(user=request.user, pk=pk).first()

    def put(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return renderResponse(data='Address not found', message='Not found', status=404)
        serializer = ShippingAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return renderResponse(data=serializer.data, message='Address updated')
        return renderResponse(data=serializer.errors, message='Validation error', status=400)

    def delete(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return renderResponse(data='Address not found', message='Not found', status=404)
        address.delete()
        return renderResponse(data=None, message='Address deleted')


# ─── Orders ─────────────────────────────────────────────────────────────────


class PlaceOrderView(APIView):
    """Place a new order (creates SalesOrder + items)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)

        data = serializer.validated_data
        items_data = data['items']

        # Validate shipping address
        address = UserShippingAddress.objects.filter(
            user=request.user, pk=data['shipping_address_id']
        ).first()
        if not address:
            return renderResponse(data='Shipping address not found', message='Invalid address', status=400)

        # Validate products and calculate totals
        order_items = []
        total_amount = 0
        for item in items_data:
            product = Products.objects.filter(pk=item['product_id'], status='ACTIVE').first()
            if not product:
                return renderResponse(
                    data=f'Product {item["product_id"]} not found or inactive',
                    message='Invalid product',
                    status=400,
                )
            price = product.discount_price if product.discount_price else product.initial_selling_price
            item_total = price * item['quantity']
            tax_amount = item_total * (product.tax_percentage / 100) if product.tax_percentage else 0
            total_amount += item_total + tax_amount
            order_items.append({
                'product': product,
                'quantity': item['quantity'],
                'size': item.get('size', ''),
                'price': price,
                'tax_percentage': product.tax_percentage,
                'tax_amount': tax_amount,
                'item_total': item_total,
            })

        # Generate order code
        so_code = f"SO-{uuid.uuid4().hex[:8].upper()}"
        now = timezone.now()

        # Map payment method
        payment_terms = 'CASH' if data['payment_method'] == 'COD' else 'ONLINE'

        # Determine domain_user_id (use product's domain if available)
        domain_user = None
        if order_items and order_items[0]['product'].domain_user_id:
            domain_user = order_items[0]['product'].domain_user_id

        # Create SalesOrder
        order = SalesOrder.objects.create(
            customer_id=request.user,
            so_code=so_code,
            so_date=now,
            expected_delivery_date=now + timedelta(days=7),
            payment_terms=payment_terms,
            payment_status='UNPAID',
            discount_amount=0,
            discount_type='NO DISCOUNT',
            shipping_amount=0,
            shipping_type='FREE',
            shipping_tax_percentage=0,
            shipping_cancelled_type='FREE',
            shipping_cancelled_amount=0,
            shipping_cancelled_tax_amount=0,
            status='DRAFT',
            created_by_user_id=request.user,
            updated_by_user_id=request.user,
            domain_user_id=domain_user,
            approved_at=now,
            cancelled_at=now,
            cancelled_reason='',
            additional_details={
                'payment_method': data['payment_method'],
                'notes': data.get('notes', ''),
                'shipping_address': {
                    'address_type': address.address_type,
                    'address': address.address,
                    'city': address.city,
                    'state': address.state,
                    'pincode': address.pincode,
                    'country': address.country,
                },
            },
        )

        # Create order items
        for item in order_items:
            SalesOrderOrderItems.objects.create(
                so_id=order,
                product_id=item['product'],
                quantity_ordered=item['quantity'],
                quantity_delivered=0,
                quantity_shipped=0,
                quantity_cancelled=0,
                quantity_returned=0,
                purchase_price=item['price'],
                tax_percentage=item['tax_percentage'],
                discount_amount=0,
                amount_paid=0,
                amount_returned=0,
                amount_cancelled=0,
                amount_ordered=item['item_total'],
                tax_amount=item['tax_amount'],
                discount_type='NO DISCOUNT',
                domain_user_id=domain_user,
                additional_details={'size': item['size']},
            )

        return renderResponse(
            data={
                'order_id': order.id,
                'so_code': order.so_code,
                'total_amount': total_amount,
                'status': order.status,
                'expected_delivery_date': order.expected_delivery_date.strftime('%Y-%m-%d'),
            },
            message='Order placed successfully',
            status=201,
        )


class CustomerOrderListView(generics.ListAPIView):
    """List customer's orders."""
    serializer_class = CustomerOrderListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        return SalesOrder.objects.filter(
            customer_id=self.request.user
        ).order_by('-created_at')

    @CommonListAPIMixin.common_list_decorator(CustomerOrderListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CustomerOrderDetailView(APIView):
    """Get a single order's details."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = SalesOrder.objects.filter(customer_id=request.user, pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)
        serializer = CustomerOrderDetailSerializer(order)
        return renderResponse(data=serializer.data, message='Order retrieved')


# ─── Customer Reviews & Questions ──────────────────────────────────────────


class CustomerReviewCreateView(APIView):
    """Submit a product review."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        rating = request.data.get('rating')
        review_text = request.data.get('review', '')
        review_images = request.data.get('review_images', [])

        if not product_id or rating is None:
            return renderResponse(data='product_id and rating are required', message='Validation error', status=400)

        product = Products.objects.filter(pk=product_id, status='ACTIVE').first()
        if not product:
            return renderResponse(data='Product not found', message='Not found', status=404)

        review = ProductReviews.objects.create(
            product_id=product,
            review_user_id=request.user,
            domain_user_id=product.domain_user_id,
            rating=float(rating),
            reviews=review_text,
            review_images=review_images if review_images else [],
            status='ACTIVE',
        )
        return renderResponse(
            data=StorefrontReviewSerializer(review).data,
            message='Review submitted',
            status=201,
        )


class CustomerQuestionCreateView(APIView):
    """Ask a product question."""
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
            product_id=product,
            question_user_id=request.user,
            answer_user_id=request.user,
            domain_user_id=product.domain_user_id,
            question=question_text,
            answer='',
            status='ACTIVE',
        )
        return renderResponse(
            data={'id': question.id, 'question': question.question},
            message='Question submitted',
            status=201,
        )


# ─── Admin endpoints ───────────────────────────────────────────────────────


class AdminDashboardView(APIView):
    """Dashboard stats for admin panel."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        domain_id = user.domain_user_id.id if user.domain_user_id else user.id
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        orders_base = SalesOrder.objects.filter(domain_user_id=domain_id)

        # Order counts
        today_orders = orders_base.filter(created_at__gte=today_start).count()
        week_orders = orders_base.filter(created_at__gte=week_start).count()
        month_orders = orders_base.filter(created_at__gte=month_start).count()
        total_orders = orders_base.count()

        # Revenue (sum of order item amounts for non-cancelled orders)
        revenue_base = SalesOrderOrderItems.objects.filter(
            so_id__domain_user_id=domain_id
        ).exclude(so_id__status='CANCELLED')

        today_revenue = revenue_base.filter(
            created_at__gte=today_start
        ).aggregate(total=Sum('amount_ordered'))['total'] or 0

        month_revenue = revenue_base.filter(
            created_at__gte=month_start
        ).aggregate(total=Sum('amount_ordered'))['total'] or 0

        # Recent orders
        recent_orders = orders_base.order_by('-created_at')[:10]
        recent_data = CustomerOrderListSerializer(recent_orders, many=True).data

        # Order status distribution
        status_counts = {}
        for order_status in ['DRAFT', 'SENT', 'DELIVERED', 'CANCELLED', 'COMPLETED']:
            status_counts[order_status] = orders_base.filter(status=order_status).count()

        # Top products (by order count)
        top_products = SalesOrderOrderItems.objects.filter(
            so_id__domain_user_id=domain_id
        ).values('product_id__name', 'product_id__slug').annotate(
            order_count=Count('id'),
            total_sold=Sum('quantity_ordered'),
        ).order_by('-order_count')[:5]

        # Product & customer counts
        total_products = Products.objects.filter(domain_user_id=domain_id, status='ACTIVE').count()
        total_customers = Users.objects.filter(domain_user_id=domain_id, role='Customer').count()

        data = {
            'orders': {
                'today': today_orders,
                'this_week': week_orders,
                'this_month': month_orders,
                'total': total_orders,
            },
            'revenue': {
                'today': float(today_revenue),
                'this_month': float(month_revenue),
            },
            'status_distribution': status_counts,
            'recent_orders': recent_data,
            'top_products': list(top_products),
            'total_products': total_products,
            'total_customers': total_customers,
        }
        return renderResponse(data=data, message='Dashboard data retrieved')


class AdminSalesOrderListView(generics.ListAPIView):
    """Admin: list all sales orders."""
    serializer_class = CustomerOrderListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        domain_id = user.domain_user_id.id if user.domain_user_id else user.id
        queryset = SalesOrder.objects.filter(domain_user_id=domain_id).order_by('-created_at')

        # Filter by status
        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        return queryset

    @CommonListAPIMixin.common_list_decorator(CustomerOrderListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AdminSalesOrderDetailView(APIView):
    """Admin: get order detail and update status."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        domain_id = user.domain_user_id.id if user.domain_user_id else user.id
        order = SalesOrder.objects.filter(domain_user_id=domain_id, pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)

        serializer = CustomerOrderDetailSerializer(order)
        data = serializer.data

        # Include customer info for admin
        if order.customer_id:
            data['customer'] = {
                'id': order.customer_id.id,
                'username': order.customer_id.username,
                'email': order.customer_id.email,
                'phone': order.customer_id.phone,
                'name': f"{order.customer_id.first_name} {order.customer_id.last_name}".strip(),
            }
        return renderResponse(data=data, message='Order retrieved')

    def patch(self, request, pk):
        user = request.user
        domain_id = user.domain_user_id.id if user.domain_user_id else user.id
        order = SalesOrder.objects.filter(domain_user_id=domain_id, pk=pk).first()
        if not order:
            return renderResponse(data='Order not found', message='Not found', status=404)

        new_status = request.data.get('status')
        valid_statuses = ['DRAFT', 'SENT', 'DELIVERED', 'PARTIAL DELIVERED', 'CANCELLED', 'RETURNED', 'COMPLETED']
        if new_status not in valid_statuses:
            return renderResponse(data=f'Invalid status. Must be one of: {valid_statuses}', message='Validation error', status=400)

        order.status = new_status
        order.updated_by_user_id = user
        order.last_updated_by_user_id = user

        if new_status == 'CANCELLED':
            order.cancelled_by_user_id = user
            order.cancelled_at = timezone.now()
            order.cancelled_reason = request.data.get('reason', '')
            order.payment_status = 'CANCELLED'

        order.save()
        return renderResponse(
            data={'id': order.id, 'status': order.status, 'so_code': order.so_code},
            message=f'Order status updated to {new_status}',
        )
