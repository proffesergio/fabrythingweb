"""Banner module: public scheduling + admin CRUD gating.

Pins the two behaviours the feature spec calls out explicitly:
  - a banner outside its starts_at/ends_at window must not be served, and
  - a non-platform user (a plain Customer) gets 403 on admin banner CRUD,
    because /api/store/ bypasses PermissionMiddleware's ModuleUrls gate
    entirely (see storefront/permissions.IsPlatformStaff).
Also covers CTA link resolution (product vs raw URL fallback) and reorder.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from catalog.models import Categories, Products
from storefront.models import Banner

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


def make_product(owner, slug="widget"):
    category = Categories.objects.create(
        name="Widgets", slug=f"widgets-{slug}", description="d",
        domain_user_id=owner, added_by_user_id=owner,
    )
    return Products.objects.create(
        name="Widget", slug=slug, description="d", sku=f"SKU-{slug}",
        initial_buying_price=100, initial_selling_price=150,
        category_id=category, domain_user_id=owner, added_by_user_id=owner,
        status="ACTIVE",
    )


class BannerSchedulingTests(TestCase):
    """A banner outside its window must not be served, and one with no
    window at all is always served while active."""

    def setUp(self):
        self.client = APIClient()
        self.now = timezone.now()

    def test_active_banner_with_no_window_is_served(self):
        Banner.objects.create(image="/api/media/abc/", headline="Always on")
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["headline"] for b in res.data["data"]], ["Always on"])

    def test_inactive_banner_is_excluded(self):
        Banner.objects.create(image="/api/media/abc/", headline="Off", is_active=False)
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.data["data"], [])

    def test_banner_not_yet_started_is_excluded(self):
        Banner.objects.create(
            image="/api/media/abc/", headline="Future",
            starts_at=self.now + timedelta(days=1),
        )
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.data["data"], [])

    def test_banner_already_ended_is_excluded(self):
        Banner.objects.create(
            image="/api/media/abc/", headline="Past",
            ends_at=self.now - timedelta(days=1),
        )
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.data["data"], [])

    def test_banner_inside_its_window_is_served(self):
        Banner.objects.create(
            image="/api/media/abc/", headline="Live now",
            starts_at=self.now - timedelta(days=1),
            ends_at=self.now + timedelta(days=1),
        )
        res = self.client.get("/api/store/banners/")
        self.assertEqual([b["headline"] for b in res.data["data"]], ["Live now"])

    def test_results_ordered_by_display_order(self):
        Banner.objects.create(image="/x/", headline="Second", display_order=2)
        Banner.objects.create(image="/x/", headline="First", display_order=1)
        res = self.client.get("/api/store/banners/")
        self.assertEqual([b["headline"] for b in res.data["data"]], ["First", "Second"])


class BannerCtaLinkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create(username="prod-owner", email="po@x.com", role="Super Admin")

    def test_cta_resolves_to_product_url_when_product_set(self):
        product = make_product(self.owner, slug="cool-widget")
        Banner.objects.create(image="/x/", headline="Buy it", cta_product=product, cta_url="https://example.com")
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.data["data"][0]["cta_link"], "/product/cool-widget")

    def test_cta_falls_back_to_raw_url_when_no_product(self):
        Banner.objects.create(image="/x/", headline="Sale", cta_url="/shop?tag=sale")
        res = self.client.get("/api/store/banners/")
        self.assertEqual(res.data["data"][0]["cta_link"], "/shop?tag=sale")

    def test_cta_link_is_null_when_neither_set(self):
        Banner.objects.create(image="/x/", headline="Just a look")
        res = self.client.get("/api/store/banners/")
        self.assertIsNone(res.data["data"][0]["cta_link"])


class BannerAdminPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="banner-admin", email="ba@x.com", role="Admin")
        self.customer = User.objects.create(username="banner-cust", email="bc@x.com", role="Customer")
        self.banner = Banner.objects.create(image="/x/", headline="Existing")

    def test_customer_gets_403_on_list(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/store/admin/banners/")
        self.assertEqual(res.status_code, 403)

    def test_customer_gets_403_on_create(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/store/admin/banners/", {"image": "/x/", "headline": "Nope"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_anonymous_gets_401_or_403(self):
        res = self.client.get("/api/store/admin/banners/")
        self.assertIn(res.status_code, (401, 403))

    def test_admin_can_list(self):
        auth(self.client, self.admin)
        res = self.client.get("/api/store/admin/banners/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["data"]), 1)

    def test_admin_can_create(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/store/admin/banners/", {
            "image": "/api/media/xyz/", "headline": "New banner",
            "animation_style": "ZOOM", "background": "#000000",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Banner.objects.count(), 2)

    def test_admin_can_update(self):
        auth(self.client, self.admin)
        res = self.client.patch(f"/api/store/admin/banners/{self.banner.id}/", {"headline": "Edited"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.headline, "Edited")

    def test_admin_can_delete(self):
        auth(self.client, self.admin)
        res = self.client.delete(f"/api/store/admin/banners/{self.banner.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Banner.objects.filter(pk=self.banner.id).exists())

    def test_admin_can_reorder(self):
        second = Banner.objects.create(image="/x/", headline="Second", display_order=1)
        auth(self.client, self.admin)
        res = self.client.post(
            "/api/store/admin/banners/reorder/",
            {"order": [second.id, self.banner.id]}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        second.refresh_from_db()
        self.banner.refresh_from_db()
        self.assertEqual(second.display_order, 0)
        self.assertEqual(self.banner.display_order, 1)


class BannerLayoutTests(TestCase):
    """A wide marketing banner and a product cut-out need different heroes.

    The original model assumed every banner is a transparent PNG composited
    beside a headline. A wide pre-rendered artwork (the kind a brand supplies)
    has its own typography baked in, so squeezing it into the split layout
    letterboxes it and repeats the text.
    """

    def test_layout_defaults_to_the_product_cutout_split(self):
        b = Banner.objects.create(image='https://x/y.png', headline='Hi')
        self.assertEqual(b.layout, Banner.Layout.PRODUCT)

    def test_full_bleed_layout_can_be_chosen(self):
        b = Banner.objects.create(image='https://x/wide.jpg', layout=Banner.Layout.FULL_BLEED)
        self.assertEqual(b.layout, 'FULL_BLEED')

    def test_headline_is_optional(self):
        # A full-bleed artwork usually carries its own wording; requiring a
        # headline forced the owner to invent one that then rendered on top.
        b = Banner(image='https://x/wide.jpg', layout=Banner.Layout.FULL_BLEED)
        b.full_clean()   # must not raise
        b.save()
        self.assertEqual(b.headline, '')

    def test_public_serializer_exposes_layout(self):
        Banner.objects.create(image='https://x/wide.jpg', layout=Banner.Layout.FULL_BLEED,
                              is_active=True)
        res = self.client.get('/api/store/banners/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['data'][0]['layout'], 'FULL_BLEED')

    def test_admin_serializer_round_trips_layout(self):
        from storefront.serializers import BannerAdminSerializer
        s = BannerAdminSerializer(data={'image': 'https://x/w.jpg', 'layout': 'FULL_BLEED'})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.save().layout, 'FULL_BLEED')

    def test_admin_serializer_accepts_a_banner_with_no_headline(self):
        from storefront.serializers import BannerAdminSerializer
        s = BannerAdminSerializer(data={'image': 'https://x/w.jpg'})
        self.assertTrue(s.is_valid(), s.errors)
