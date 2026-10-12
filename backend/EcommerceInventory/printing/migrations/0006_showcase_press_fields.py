# Showcase upgrade for the ColorLifePrint-style storefront: press categories,
# badges, BDT prices, multi-format design files, top-pick flags and an
# orderable press-product link. The garment categories stay valid so the
# t-shirt custom-request showcase keeps working untouched.
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('printing', '0005_seed_press_catalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printshowcaseitem',
            name='category',
            field=models.CharField(choices=[('apparel', 'Apparel'), ('headwear-bags', 'Headwear & bags'), ('drinkware', 'Drinkware'), ('office', 'Office & stationery'), ('accessories-tech', 'Accessories & tech'), ('business-cards', 'Business Cards'), ('flyers-brochures', 'Flyers & Brochures'), ('brochures-catalogues', 'Brochures & Catalogues'), ('office-packaging', 'Office & Packaging'), ('box-packaging', 'Box & Packaging'), ('stickers-labels', 'Stickers & Labels'), ('signage-outdoor', 'Signage & Outdoor Branding'), ('flags-display', 'Flags & Outdoor Display'), ('large-format', 'Large Format Printing'), ('corporate-stationery', 'Corporate Stationery'), ('letterheads', 'Letterheads'), ('posters', 'Posters'), ('promotional', 'Promotional Products')], default='apparel', max_length=32),
        ),
        migrations.AlterField(
            model_name='printshowcaseitem',
            name='image',
            field=models.URLField(blank=True, default='', help_text='Preview thumbnail. For image uploads this is the file itself.', max_length=500),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='file_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='file_type',
            field=models.CharField(blank=True, default='', max_length=12),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='badge',
            field=models.CharField(blank=True, choices=[('', 'None'), ('HOT', 'Hot'), ('NEW', 'New'), ('OFFER', 'Offer')], default='', max_length=8),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='price_bdt',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='is_top_pick',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='printshowcaseitem',
            name='press_product',
            field=models.ForeignKey(blank=True, help_text='Orderable press product this design showcases (Order-now handoff).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='showcase_items', to='printing.pressproduct'),
        ),
    ]
