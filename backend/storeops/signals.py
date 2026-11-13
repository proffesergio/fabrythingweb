from catalog.models import Products
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Products, dispatch_uid="storeops_new_product_images")
def enqueue_new_product_images(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        from .images import enqueue_product
        from .models import OperationsPolicy

        if OperationsPolicy.current().auto_clean_images:
            enqueue_product(instance)
