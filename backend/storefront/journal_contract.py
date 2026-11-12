"""Versioned structured content, never arbitrary executable HTML."""
import re
from urllib.parse import urlsplit
from rest_framework import serializers

INTENTS = ('how_to', 'troubleshooting', 'buying_guide', 'comparison', 'ecosystem')


def public_url(value):
    from ipaddress import ip_address
    parsed = urlsplit(value)
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme != 'https' or not host or parsed.username or parsed.password or host == 'localhost' or host.endswith(('.local', '.localhost')):
        raise serializers.ValidationError('Use a public HTTPS content URL without credentials.')
    try:
        if not ip_address(host).is_global:
            raise serializers.ValidationError('Private content URLs are not allowed.')
    except ValueError:
        pass
    return value


class SourceSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    url = serializers.CharField(max_length=2000, validators=[public_url])


class ReviewSerializer(serializers.Serializer):
    author = serializers.CharField(max_length=120)
    body = serializers.CharField(max_length=1500)
    sourceUrl = serializers.CharField(max_length=2000, validators=[public_url])
    datePublished = serializers.DateField()


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=200)
    platform = serializers.ChoiceField(choices=('fabrything', 'amazon', 'alibaba', 'other'))
    url = serializers.CharField(max_length=2000, validators=[public_url])
    sourceUrl = serializers.CharField(max_length=2000, validators=[public_url])
    image = serializers.CharField(max_length=2000, validators=[public_url], required=False)
    imageAlt = serializers.CharField(max_length=250, required=False, default='')
    specs = serializers.DictField(child=serializers.CharField(max_length=300), default=dict)
    review = ReviewSerializer(required=False)

    def validate(self, data):
        if len(data['specs']) > 12 or any(len(k) > 100 for k in data['specs']):
            raise serializers.ValidationError('Use at most twelve short specification labels.')
        host = urlsplit(data['url']).hostname.lower()
        if data['platform'] == 'fabrything' and host not in ('fabrything.com', 'www.fabrything.com'):
            raise serializers.ValidationError('Store products must link to Fabrything.')
        if data['platform'] == 'amazon' and not (re.fullmatch(r'(?:[a-z0-9-]+\.)?amazon\.(?:com|co\.uk|in|de|fr|ca|co\.jp|com\.au)', host) or host == 'amzn.to'):
            raise serializers.ValidationError('Amazon products must link to an approved Amazon domain.')
        if data['platform'] == 'alibaba' and not (host == 'alibaba.com' or host.endswith('.alibaba.com')):
            raise serializers.ValidationError('Alibaba products must link to Alibaba.')
        return data


class JournalPayloadSerializer(serializers.Serializer):
    version = serializers.ChoiceField(choices=('fabrything-journal-v1',))
    sourceKey = serializers.RegexField(r'^[A-Za-z0-9:_-]{1,240}$')
    workspaceId = serializers.UUIDField()
    pageId = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=180)
    excerpt = serializers.CharField(max_length=300)
    seoTitle = serializers.CharField(max_length=255)
    seoDescription = serializers.CharField(max_length=300)
    keyword = serializers.CharField(max_length=160)
    problem = serializers.CharField(max_length=300)
    audience = serializers.CharField(max_length=200)
    intent = serializers.ChoiceField(choices=INTENTS)
    clusterSlug = serializers.SlugField(max_length=140)
    tags = serializers.ListField(child=serializers.CharField(max_length=60), max_length=10, default=list)
    sources = SourceSerializer(many=True, allow_empty=False)
    products = ProductSerializer(many=True, default=list)
    blocks = serializers.ListField(child=serializers.DictField(), min_length=3, max_length=45)
    editorial = serializers.DictField(default=dict)
    publish = serializers.BooleanField(default=False)

    def validate(self, data):
        if len(data['sources']) > 12 or len(data['products']) > 12:
            raise serializers.ValidationError('At most twelve sources and products are supported.')
        ids = {p['id'] for p in data['products']}
        if len(ids) != len(data['products']):
            raise serializers.ValidationError('Product IDs must be unique.')
        image_seen = False
        for b in data['blocks']:
            kind = b.get('type')
            if kind in ('paragraph', 'heading', 'verdict'):
                if not isinstance(b.get('text'), str) or not b['text'].strip() or len(b['text']) > 4000:
                    raise serializers.ValidationError('Text blocks need bounded, complete text.')
                for key in list(b):
                    if key not in ('type', 'text'):
                        del b[key]
            elif kind in ('comparison', 'products'):
                references = b.get('productIds', [])
                if not isinstance(references, list) or not references or len(references) > 12 or any(x not in ids for x in references):
                    raise serializers.ValidationError('Product blocks must reference supplied product IDs.')
                criteria = b.get('criteria', [])
                if not isinstance(criteria, list) or len(criteria) > 12 or any(not isinstance(x, str) or len(x) > 100 for x in criteria):
                    raise serializers.ValidationError('Comparison criteria must be short labels.')
            elif kind == 'pros_cons':
                if any(not isinstance(b.get(k), list) or len(b[k]) > 8 or any(not isinstance(x, str) or len(x) > 400 for x in b[k]) for k in ('pros', 'cons')):
                    raise serializers.ValidationError('Pros and cons must be bounded text lists.')
            elif kind == 'faq':
                items = b.get('items')
                if not isinstance(items, list) or not 1 <= len(items) <= 8 or any(not isinstance(x, dict) or any(not isinstance(x.get(k), str) or not x[k].strip() or len(x[k]) > 1500 for k in ('question', 'answer')) for x in items):
                    raise serializers.ValidationError('FAQ blocks need complete questions and answers.')
            elif kind == 'image':
                image_seen = True
                if not isinstance(b.get('alt'), str) or not b['alt'].strip() or len(b['alt']) > 250:
                    raise serializers.ValidationError('Every image or image placeholder needs descriptive alt text.')
                for dimension in ('width', 'height'):
                    if type(b.get(dimension)) is not int or not 100 <= b[dimension] <= 4000:
                        raise serializers.ValidationError('Images require explicit safe dimensions.')
                if b.get('src'):
                    public_url(b['src'])
                variants = b.get('variants', [])
                if not isinstance(variants, list) or len(variants) > 4 or any(not isinstance(v, dict) or type(v.get('width')) is not int or not 100 <= v['width'] <= 4000 or not isinstance(v.get('src'), str) for v in variants):
                    raise serializers.ValidationError('Use at most four responsive image variants.')
                for v in variants:
                    public_url(v['src'])
            else:
                raise serializers.ValidationError('Unknown journal block type.')
        if not image_seen or not any(b['type'] == 'heading' for b in data['blocks']):
            raise serializers.ValidationError('An article requires section headings and an image plan.')
        return data
