from django.db import models
from django.utils.text import slugify

from UserServices.models import Users

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
    discount_price=models.FloatField(blank=True,null=True)
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