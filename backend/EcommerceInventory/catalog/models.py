from django.db import models
from django.utils.text import slugify

from accounts.models import Users

# Create your models here.
class Categories(models.Model):
    id=models.AutoField(primary_key=True)
    name=models.CharField(max_length=255)
    slug=models.SlugField(max_length=255,unique=True,blank=True)
    image=models.JSONField(blank=True,null=True)
    description=models.TextField()
    display_order=models.IntegerField(default=0)
    parent_id=models.ForeignKey('self',on_delete=models.CASCADE,blank=True,null=True)
    domain_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='domain_user_id_category')
    added_by_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='added_by_user_id_category')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def defaultkey():
        return "name"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


GENDER_CHOICES = [
    ('MEN', 'Men'),
    ('WOMEN', 'Women'),
    ('KIDS', 'Kids'),
    ('UNISEX', 'Unisex'),
]

SIZE_CHOICES = [
    ('XS', 'XS'),
    ('S', 'S'),
    ('M', 'M'),
    ('L', 'L'),
    ('XL', 'XL'),
    ('XXL', 'XXL'),
    ('XXXL', 'XXXL'),
    ('FREE', 'Free Size'),
]

class Products(models.Model):
    id=models.AutoField(primary_key=True)
    name=models.CharField(max_length=255,blank=True,null=True)
    slug=models.SlugField(max_length=255,unique=True,blank=True)
    image=models.JSONField(default=list,blank=True)
    description=models.TextField()
    specifications=models.JSONField(default=dict,blank=True)
    html_description=models.TextField(blank=True,default='')
    highlights=models.JSONField(default=list,blank=True)
    sku=models.CharField(max_length=255)
    initial_buying_price=models.FloatField()
    initial_selling_price=models.FloatField()
    # The supplier/source price BEFORE the platform markup (catalog/pricing.py
    # apply_markup). Selling price is always derived from this, never mutated
    # in place -- re-running an import/sync/backfill must be able to recompute
    # the same selling price every time instead of stacking the markup on top
    # of itself. Nullable because the 194 products that predate this feature
    # have none yet; `apply_pricing_markup` backfills it from today's
    # initial_selling_price (today's un-marked-up price) on first run.
    base_price=models.FloatField(blank=True,null=True)
    discount_price=models.FloatField(blank=True,null=True)
    # Per-product shipping override. NULL (the default) means "use the
    # store's flat rate" (core.models.StoreConfiguration.fixed_shipping_rate)
    # -- this must stay distinct from an explicit 0, which means this
    # specific product ships free. Order-level shipping is the max() of the
    # store's flat rate and every distinct per-product fee in the cart (see
    # core.models.StoreConfiguration.shipping_for) -- one delivery trip, and
    # the bulkiest/most expensive-to-ship item sets the cost.
    shipping_fee=models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Per-product shipping fee. Leave blank to use the store's "
                  "flat rate; 0 means this product ships free.",
    )
    # Explicit "free shipping promo" flag -- distinct from shipping_fee=0.
    # shipping_fee=0 is still just a candidate in shipping_for()'s max(), so
    # the flat rate floor can (and usually does) override it; free_shipping
    # actually waives this product's shipping outright. A cart made up
    # entirely of free_shipping products ships free; in a mixed cart the
    # promo items are excluded from the max() rather than the whole order
    # going free or the promo item dragging the charge down (see
    # core.models.StoreConfiguration.shipping_for). Defaults False so every
    # existing product is unaffected until an admin opts it in.
    free_shipping=models.BooleanField(
        default=False,
        help_text="Mark this product as an explicit free-shipping promo item.",
    )
    weight=models.FloatField(blank=True,null=True)
    dimensions=models.CharField(default='0x0x0',max_length=255,blank=True)
    uom=models.CharField(max_length=255,default='PCS',blank=True)
    color=models.CharField(max_length=255,blank=True,default='')
    tax_percentage=models.FloatField(default=0)
    brand=models.CharField(max_length=255,blank=True,default='')
    brand_model=models.CharField(max_length=255,blank=True,default='')
    status=models.CharField(max_length=255,choices=[('ACTIVE','ACTIVE'),('INACTIVE','INACTIVE')],default='ACTIVE')
    # Clothing-specific fields
    gender=models.CharField(max_length=10,choices=GENDER_CHOICES,default='UNISEX')
    available_sizes=models.JSONField(default=list,blank=True,help_text='List of available sizes, e.g. ["S","M","L","XL"]')
    size_chart=models.JSONField(default=dict,blank=True,help_text='Size measurements in inches, e.g. {"S":{"chest":36,"length":27},"M":{"chest":38,"length":28}}')
    material=models.CharField(max_length=255,blank=True,default='',help_text='e.g. Cotton, Polyester, Silk')
    # SEO
    seo_title=models.CharField(max_length=255,blank=True,default='')
    seo_description=models.TextField(blank=True,default='')
    seo_keywords=models.JSONField(default=list,blank=True)
    # Reseller source (partner stores we sync prices from)
    source_url=models.URLField(max_length=500,blank=True,default='')
    source_price=models.FloatField(blank=True,null=True)
    price_synced_at=models.DateTimeField(blank=True,null=True)
    addition_details=models.JSONField(default=dict,blank=True)
    category_id=models.ForeignKey(Categories,on_delete=models.CASCADE,blank=True,null=True,related_name='category_id_products')
    domain_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='domain_user_id_products')
    added_by_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='added_by_user_id_products')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or f"Product #{self.id}"

    @property
    def total_stock(self):
        """Sellable units across all active variants."""
        return sum(v.stock_quantity for v in self.variants.filter(is_active=True))


class ProductVariant(models.Model):
    """
    A sellable SKU for a product (e.g. a specific size/color).

    ``stock_quantity`` is the authoritative sellable count that the COD
    checkout locks with select_for_update() and decrements atomically.
    """
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    size = models.CharField(max_length=16, blank=True, default="")
    color = models.CharField(max_length=32, blank=True, default="")
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Selling price for this variant (overrides product price).",
    )
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    weight_grams = models.PositiveIntegerField(default=0, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"], name="uq_variant_product_size_color"
            )
        ]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["product", "is_active"]),
        ]

    def __str__(self):
        bits = [self.product.name or f"Product #{self.product_id}"]
        if self.size:
            bits.append(self.size)
        if self.color:
            bits.append(self.color)
        return " / ".join(bits)

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price is not None else self.price

    @property
    def in_stock(self):
        return self.is_active and self.stock_quantity > 0

class ProductQuestions(models.Model):
    id=models.AutoField(primary_key=True)
    question=models.TextField()
    answer=models.TextField()
    status=models.CharField(max_length=255,choices=[('ACTIVE','ACTIVE'),('INACTIVE','INACTIVE')],default='ACTIVE')
    product_id=models.ForeignKey(Products,on_delete=models.CASCADE,blank=True,null=True,related_name='product_id_questions')
    domain_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='domain_user_id_questions')
    question_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='questions_by_user_id_questions')
    answer_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='answer_by_user_id_questions')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class ProductReviews(models.Model):
    id=models.AutoField(primary_key=True)
    review_images=models.JSONField()
    rating=models.FloatField()
    reviews=models.TextField()
    status=models.CharField(max_length=255,choices=[('ACTIVE','ACTIVE'),('INACTIVE','INACTIVE')],default='ACTIVE')
    product_id=models.ForeignKey(Products,on_delete=models.CASCADE,blank=True,null=True,related_name='product_id_reviews')
    domain_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='domain_user_id_reviews')
    review_user_id=models.ForeignKey(Users,on_delete=models.CASCADE,blank=True,null=True,related_name='added_by_user_id_reviews')
    created_at=models.DateTimeField(auto_now_add=True)