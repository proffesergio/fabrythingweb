from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AdConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adsense_client', models.CharField(blank=True, default='', max_length=64)),
                ('slot_top', models.CharField(blank=True, default='', max_length=32)),
                ('slot_inarticle_1', models.CharField(blank=True, default='', max_length=32)),
                ('slot_inarticle_2', models.CharField(blank=True, default='', max_length=32)),
                ('slot_sidebar', models.CharField(blank=True, default='', max_length=32)),
                ('slot_multiplex', models.CharField(blank=True, default='', max_length=32)),
                ('slot_shop_subtle', models.CharField(blank=True, default='', max_length=32)),
                ('auto_ads_low_sitewide', models.BooleanField(default=True)),
                ('news_detail_max_ads', models.BooleanField(default=True)),
                ('shop_ads_enabled', models.BooleanField(default=False)),
                ('anchor_on_news_only', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Ad config', 'verbose_name_plural': 'Ad config'},
        ),
        migrations.CreateModel(
            name='NewsCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=140, unique=True)),
                ('description', models.CharField(blank=True, default='', max_length=300)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['display_order', 'name'], 'verbose_name': 'News category', 'verbose_name_plural': 'News categories'},
        ),
        migrations.CreateModel(
            name='TrendKeyword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyword', models.CharField(db_index=True, max_length=255)),
                ('geo', models.CharField(default='BD', max_length=8)),
                ('traffic_score', models.IntegerField(default=0)),
                ('traffic_label', models.CharField(blank=True, default='', max_length=60)),
                ('category_hint', models.CharField(blank=True, default='', max_length=120)),
                ('status', models.CharField(choices=[('NEW', 'New'), ('USED', 'Used (draft created)'), ('IGNORED', 'Ignored')], default='NEW', max_length=10)),
                ('fetched_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-traffic_score', '-fetched_at'], 'verbose_name': 'Trend keyword', 'verbose_name_plural': 'Trend keywords'},
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('headline', models.CharField(help_text='Engaging headline (Bangla viral + EN keyword)', max_length=255)),
                ('headline_bn', models.CharField(blank=True, default='', help_text='Optional pure-Bangla display headline', max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=200, unique=True)),
                ('excerpt', models.CharField(blank=True, default='', max_length=300)),
                ('body_html', models.TextField(help_text='Full 600-1000 word article HTML from admin editor')),
                ('hero_image', models.CharField(blank=True, default='', help_text='Upload via POST /api/uploads/ then paste URL here', max_length=500)),
                ('hero_image_alt', models.CharField(blank=True, default='', max_length=255)),
                ('image_credit', models.CharField(blank=True, default='', max_length=255)),
                ('source_name', models.CharField(blank=True, default='', max_length=255)),
                ('source_url', models.URLField(blank=True, default='', max_length=500)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('REVIEW', 'In review'), ('PUBLISHED', 'Published'), ('ARCHIVED', 'Archived')], db_index=True, default='DRAFT', max_length=10)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_breaking', models.BooleanField(default=False)),
                ('related_product_ids', models.JSONField(blank=True, default=list)),
                ('seo_title', models.CharField(blank=True, default='', max_length=255)),
                ('seo_description', models.CharField(blank=True, default='', max_length=300)),
                ('seo_keywords', models.JSONField(blank=True, default=list)),
                ('fb_post_url', models.URLField(blank=True, default='', max_length=500)),
                ('utm_campaign', models.CharField(blank=True, default='nobleseek-fb', max_length=120)),
                ('view_count', models.PositiveIntegerField(default=0)),
                ('read_time_minutes', models.PositiveSmallIntegerField(default=3)),
                ('published_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles', to='nobleseek.newscategory')),
                ('trend', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles', to='nobleseek.trendkeyword')),
            ],
            options={'ordering': ['-published_at', '-created_at']},
        ),
        migrations.AddIndex(model_name='trendkeyword', index=models.Index(fields=['status', '-fetched_at'], name='nobleseek_tr_status_idx')),
        migrations.AddIndex(model_name='article', index=models.Index(fields=['status', '-published_at'], name='nobleseek_ar_status_idx')),
        migrations.AddIndex(model_name='article', index=models.Index(fields=['category', 'status'], name='nobleseek_ar_cat_idx')),
    ]
