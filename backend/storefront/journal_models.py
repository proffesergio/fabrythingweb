"""Store journal extensions; existing NobleSeek articles and URLs stay intact."""
from django.core.exceptions import ValidationError
from django.db import models


class TopicCluster(models.Model):
    LEVELS = ('industry', 'category', 'subcategory', 'micro_niche', 'buyer_intent')
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    level = models.PositiveSmallIntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    description = models.CharField(max_length=300, blank=True)
    active = models.BooleanField(default=True)

    def clean(self):
        if self.level not in range(5):
            raise ValidationError('A topic must use one of the five supported silo levels.')
        if (self.level == 0 and self.parent_id) or (self.level > 0 and not self.parent_id):
            raise ValidationError('Only the industry root can have no parent.')
        if self.parent_id and (self.parent_id == self.pk or self.parent.level != self.level - 1):
            raise ValidationError('Topic parents must be exactly one level above their child.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class JournalArticle(models.Model):
    article = models.OneToOneField('nobleseek.Article', on_delete=models.CASCADE, related_name='journal')
    cluster = models.ForeignKey(TopicCluster, null=True, blank=True, on_delete=models.PROTECT, related_name='articles')
    intent = models.CharField(max_length=24, default='how_to')
    problem = models.CharField(max_length=300)
    audience = models.CharField(max_length=200)
    keyword = models.CharField(max_length=160)
    blocks = models.JSONField(default=list)
    products = models.JSONField(default=list)
    sources = models.JSONField(default=list)
    editorial = models.JSONField(default=dict)
    source_key = models.CharField(max_length=240, unique=True)
    payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['cluster', 'intent'], name='journal_cluster_intent')]
