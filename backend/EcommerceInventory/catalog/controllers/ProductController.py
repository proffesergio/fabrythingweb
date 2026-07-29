from accounts.models import Users
from core.helpers import CommonListAPIMixin, CustomPageNumberPagination, absolutize_image_list, createParsedCreatedAtUpdatedAt, isPlatformScope, renderResponse
from catalog.category_tree import descendant_category_ids
from catalog.models import Categories, ProductQuestions, ProductReviews, Products, ProductVariant
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
    total_stock=serializers.SerializerMethodField()
    variant_count=serializers.SerializerMethodField()
    class Meta:
        model = Products
        fields = '__all__'

    def get_image(self,obj):
        # BUG 1: Products.image can hold a relative /api/media/<sha256>/ path
        # (core.storage.save_file's DB-blob fallback) — absolutize it here too,
        # same as the storefront serializer, so the admin panel image previews
        # don't 404 either. See core.helpers.absolutize_media_url.
        return absolutize_image_list(obj.image, self.context.get('request'))

    def get_total_stock(self,obj):
        # Surfaced so the admin all-products list can show a stock number
        # without an extra request per row -- stock itself lives on
        # ProductVariant, not this row (see AdminProductQuickUpdateView).
        return obj.total_stock

    def get_variant_count(self,obj):
        # Lets the admin list decide whether stock is directly inline-editable
        # (exactly one variant) or needs the per-variant picker (several).
        return obj.variants.count()

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

        category_param = self.request.query_params.get('category')
        if category_param:
            # Browse-by-category filter for the admin product list. The
            # taxonomy is 3 levels deep and products live in the leaves, so
            # this must walk the whole subtree (catalog.category_tree,
            # shared with the storefront filter) rather than matching only
            # direct children -- see BUG 2 in category_tree.py.
            lookup = Q(id=category_param) if str(category_param).isdigit() else Q(slug=category_param)
            category = Categories.objects.filter(lookup).first()
            if category:
                queryset = queryset.filter(category_id__in=descendant_category_ids(category))
            else:
                # An unrecognised category must return nothing, not silently
                # fall through to the whole catalog -- see BUG 3 in
                # storefront/views.py, the same trap on the storefront side.
                queryset = queryset.none()
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


def _variant_summary(variant):
    return {
        "id": variant.id,
        "sku": variant.sku,
        "size": variant.size,
        "color": variant.color,
        "stock_quantity": variant.stock_quantity,
        "price": float(variant.price),
        "discount_price": float(variant.discount_price) if variant.discount_price is not None else None,
    }


class AdminProductQuickUpdateView(APIView):
    """PATCH /api/products/admin/<pk>/quick-update/

    Patches only the "quick" fields the all-products list edits inline, so an
    admin can fix a price/stock typo without opening the full edit form.
    Platform-scope only (Super Admin or a domain-root user), same rule as
    every other admin catalog endpoint (core.helpers.isPlatformScope).

    Editable fields -- nothing else, and never source_url/source_price (those
    belong to the partner price sync in services_price_sync.py):
      - initial_selling_price (float, > 0)
      - discount_price (float or null; must be < the selling price in effect
        after this same request, i.e. the new price if one was sent)
      - status ("ACTIVE" / "INACTIVE") -- availability
      - shipping_fee (float >= 0, or null). Null means "use the store's flat
        rate" -- distinct from an explicit 0, which means this product ships
        free. Order-level shipping is computed from this field in exactly one
        place, core.models.StoreConfiguration.shipping_for; nothing here
        recomputes it.
      - free_shipping (bool). The explicit "free shipping promo" flag --
        distinct from shipping_fee == 0 (see the model field's docstring in
        catalog/models.py and core.models.StoreConfiguration.shipping_for).
      - stock_quantity -- lives on ProductVariant, not Products. A product
        with exactly one variant is updated directly. A product with several
        variants requires an explicit `variant_id` in the body; without one
        the request is rejected (field_errors.variant_id) rather than
        silently guessing which SKU the number belongs to. The response
        always includes the full `variants` list so the UI can offer a
        per-variant picker.

    Price changes are mirrored onto every ACTIVE variant's price/discount_price,
    matching the precedent in services_price_sync.sync_source_prices: checkout
    charges ProductVariant.effective_price, not the Products row, so the two
    must never be allowed to disagree.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    ALLOWED_STATUSES = {"ACTIVE", "INACTIVE"}

    def patch(self, request, pk):
        if not isPlatformScope(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        try:
            product = Products.objects.get(pk=pk)
        except Products.DoesNotExist:
            return renderResponse(data='Product not found', message='Not Found', status=404)

        data = request.data
        errors = {}
        update_fields = []

        # --- initial_selling_price -------------------------------------
        new_selling_price = product.initial_selling_price
        if 'initial_selling_price' in data:
            raw = data.get('initial_selling_price')
            try:
                new_selling_price = float(raw)
            except (TypeError, ValueError):
                errors['initial_selling_price'] = ['Must be a number.']
            else:
                if new_selling_price <= 0:
                    errors['initial_selling_price'] = ['Must be greater than 0.']

        # --- discount_price ----------------------------------------------
        new_discount_price = product.discount_price
        discount_provided = 'discount_price' in data
        if discount_provided:
            raw = data.get('discount_price')
            if raw is None or raw == '':
                new_discount_price = None
            else:
                try:
                    new_discount_price = float(raw)
                except (TypeError, ValueError):
                    errors['discount_price'] = ['Must be a number.']

        if 'discount_price' not in errors and new_discount_price is not None \
                and 'initial_selling_price' not in errors:
            if new_discount_price >= new_selling_price:
                errors['discount_price'] = ['Discount price must be less than the selling price.']

        # --- status (availability) ---------------------------------------
        new_status = product.status
        if 'status' in data:
            new_status = data.get('status')
            if new_status not in self.ALLOWED_STATUSES:
                errors['status'] = [f"Must be one of {sorted(self.ALLOWED_STATUSES)}."]

        # --- shipping_fee --------------------------------------------------
        # None means "use the store flat rate"; an explicit 0 means this
        # product ships free -- the two must not be conflated (see the model
        # field's docstring in catalog/models.py).
        new_shipping_fee = product.shipping_fee
        shipping_fee_provided = 'shipping_fee' in data
        if shipping_fee_provided:
            raw = data.get('shipping_fee')
            if raw is None or raw == '':
                new_shipping_fee = None
            else:
                try:
                    new_shipping_fee = float(raw)
                except (TypeError, ValueError):
                    errors['shipping_fee'] = ['Must be a number.']
                else:
                    if new_shipping_fee < 0:
                        errors['shipping_fee'] = ['Cannot be negative.']

        # --- free_shipping (explicit promo flag) --------------------------
        # Distinct from shipping_fee == 0 -- see the model field's docstring.
        new_free_shipping = product.free_shipping
        free_shipping_provided = 'free_shipping' in data
        if free_shipping_provided:
            raw = data.get('free_shipping')
            if isinstance(raw, bool):
                new_free_shipping = raw
            else:
                errors['free_shipping'] = ['Must be true or false.']

        # --- stock_quantity (lives on ProductVariant) ---------------------
        target_variant = None
        new_stock_quantity = None
        if 'stock_quantity' in data:
            raw = data.get('stock_quantity')
            try:
                new_stock_quantity = int(raw)
            except (TypeError, ValueError):
                errors['stock_quantity'] = ['Must be a whole number.']
            else:
                if new_stock_quantity < 0:
                    errors['stock_quantity'] = ['Cannot be negative.']

            if 'stock_quantity' not in errors:
                variants = list(product.variants.all())
                variant_id = data.get('variant_id')
                if variant_id:
                    target_variant = next((v for v in variants if v.id == int(variant_id)), None)
                    if target_variant is None:
                        errors['variant_id'] = ['Variant does not belong to this product.']
                elif len(variants) == 1:
                    target_variant = variants[0]
                elif len(variants) == 0:
                    errors['stock_quantity'] = ['This product has no variants to hold stock.']
                else:
                    errors['variant_id'] = [
                        'This product has multiple variants; specify variant_id to update its stock.']

        if errors:
            return renderResponse(data=errors, message='Validation error', status=400)

        # --- apply -----------------------------------------------------
        if 'initial_selling_price' in data:
            product.initial_selling_price = new_selling_price
            update_fields.append('initial_selling_price')
        if discount_provided:
            product.discount_price = new_discount_price
            update_fields.append('discount_price')
        if 'status' in data:
            product.status = new_status
            update_fields.append('status')
        if shipping_fee_provided:
            product.shipping_fee = new_shipping_fee
            update_fields.append('shipping_fee')
        if free_shipping_provided:
            product.free_shipping = new_free_shipping
            update_fields.append('free_shipping')

        if update_fields:
            update_fields.append('updated_at')
            product.save(update_fields=update_fields)

        # Keep every active variant's price in agreement with the product --
        # same rule services_price_sync.sync_source_prices follows, because
        # checkout charges ProductVariant.effective_price, not this row.
        if 'initial_selling_price' in data or discount_provided:
            product.variants.filter(is_active=True).update(
                price=new_selling_price, discount_price=new_discount_price)

        if target_variant is not None:
            target_variant.stock_quantity = new_stock_quantity
            target_variant.save(update_fields=['stock_quantity', 'updated_at'])

        variants = [_variant_summary(v) for v in product.variants.all()]
        response_data = {
            "id": product.id,
            "initial_selling_price": product.initial_selling_price,
            "discount_price": product.discount_price,
            "status": product.status,
            "shipping_fee": float(product.shipping_fee) if product.shipping_fee is not None else None,
            "free_shipping": product.free_shipping,
            "variants": variants,
        }
        return renderResponse(data=response_data, message='Product updated')


class AdminBulkShippingFeeView(APIView):
    """POST /api/products/admin/shipping-fee/bulk/

    Sets ``shipping_fee`` on many products in one call -- the owner asked to
    be able to apply a fee to "all or individual products", and doing that
    one quick-update PATCH at a time doesn't scale to a catalog-wide change.

    Body: ``{"shipping_fee": <number or null>, "product_ids": [...]}`` OR
    ``{"shipping_fee": ..., "category": <id or slug>}`` -- exactly one of
    ``product_ids``/``category``. ``category`` reuses
    ``catalog.category_tree.descendant_category_ids`` (the same whole-subtree
    walk the admin/storefront category filters use) so "apply to a category"
    means the *whole* subtree, not just its direct products, and can't drift
    from those filters.

    ``free_shipping`` (bool) can be sent alongside or instead of
    ``shipping_fee`` -- e.g. to promo a whole category as free-shipping
    without touching its per-product fee. At least one of the two must be
    present.

    Same authorization as quick-update (isPlatformScope) and the same
    field_errors validation shape. Negative fees are rejected. The match is
    capped at MAX_BATCH rows so a fat-fingered top-level category can't silently
    rewrite the entire catalog in one request -- narrow the selection instead.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    MAX_BATCH = 2000

    def post(self, request):
        if not isPlatformScope(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        data = request.data
        errors = {}

        shipping_fee = None
        shipping_fee_provided = 'shipping_fee' in data
        free_shipping_provided = 'free_shipping' in data

        if not shipping_fee_provided and not free_shipping_provided:
            errors['shipping_fee'] = ['Provide shipping_fee and/or free_shipping.']
        elif shipping_fee_provided:
            raw = data.get('shipping_fee')
            if raw is None or raw == '':
                shipping_fee = None
            else:
                try:
                    shipping_fee = float(raw)
                except (TypeError, ValueError):
                    errors['shipping_fee'] = ['Must be a number.']
                else:
                    if shipping_fee < 0:
                        errors['shipping_fee'] = ['Cannot be negative.']

        free_shipping = None
        if free_shipping_provided:
            raw = data.get('free_shipping')
            if isinstance(raw, bool):
                free_shipping = raw
            else:
                errors['free_shipping'] = ['Must be true or false.']

        product_ids = data.get('product_ids')
        category_param = data.get('category')

        if product_ids and category_param:
            errors['product_ids'] = ['Specify either product_ids or category, not both.']
        elif product_ids is not None and (not isinstance(product_ids, list) or not product_ids):
            errors['product_ids'] = ['Must be a non-empty list of product ids.']
        elif not product_ids and not category_param:
            errors['product_ids'] = ['Specify product_ids or category.']

        if errors:
            return renderResponse(data=errors, message='Validation error', status=400)

        if product_ids:
            queryset = Products.objects.filter(id__in=product_ids)
        else:
            lookup = Q(id=category_param) if str(category_param).isdigit() else Q(slug=category_param)
            category = Categories.objects.filter(lookup).first()
            if not category:
                return renderResponse(
                    data={'category': ['Category not found.']}, message='Validation error', status=400)
            queryset = Products.objects.filter(category_id__in=descendant_category_ids(category))

        total = queryset.count()
        if total == 0:
            return renderResponse(
                data={'product_ids': ['No matching products.']}, message='Validation error', status=400)
        if total > self.MAX_BATCH:
            return renderResponse(
                data={'product_ids': [
                    f'Matches {total} products; batches are capped at {self.MAX_BATCH}. Narrow the selection.'
                ]},
                message='Validation error', status=400)

        update_kwargs = {}
        if shipping_fee_provided:
            update_kwargs['shipping_fee'] = shipping_fee
        if free_shipping_provided:
            update_kwargs['free_shipping'] = free_shipping

        updated = queryset.update(**update_kwargs)
        response_data = {'updated': updated}
        if shipping_fee_provided:
            response_data['shipping_fee'] = shipping_fee
        if free_shipping_provided:
            response_data['free_shipping'] = free_shipping
        return renderResponse(data=response_data, message='Shipping fee updated')


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
