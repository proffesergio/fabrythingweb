"""Tests for the web-to-press engine: pricing formula, checkout snapshot,
status matrix, showcase upload validation and the print overview."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from printing.models import (
    FinishingOption, PaperStock, PressOrder, PressProduct, PressShopConfig,
    PressSizePreset, PrintShowcaseItem,
)
from printing.services_press import compute_press_quote, to_sq_inch
from printing.tests.helpers import auth, make_customer, make_staff


def make_press_product(name="Test Cards", slug="test-cards"):
    product = PressProduct.objects.create(
        name=name, slug=slug, category="cards",
        base_setup_cost=Decimal("150"), per_sq_inch_rate=Decimal("0.80"),
        min_qty=1, weight_per_unit_kg=Decimal("0.005"),
    )
    PressSizePreset.objects.create(
        product=product, name='3.5"x2"', width=Decimal("3.5"), height=Decimal("2"), unit="in",
    )
    return product


class PressQuoteTests(TestCase):
    def test_formula_total_matches_spec(self):
        product = make_press_product()
        paper, _ = PaperStock.objects.get_or_create(
            name="300gsm Art Card", defaults={"multiplier": Decimal("1.6")},
        )
        paper.multiplier = Decimal("1.6")
        paper.save(update_fields=["multiplier", "updated_at"])
        finish, _ = FinishingOption.objects.get_or_create(
            kind="LAMINATION", name="Glossy Test",
            defaults={"price": Decimal("3"), "per_unit": True},
        )
        quote = compute_press_quote(
            product=product, width=Decimal("3.5"), height=Decimal("2"), unit="in",
            paper_stock=paper, finishing_options=[finish], quantity=100, sides="4/0",
        )
        area = to_sq_inch(Decimal("3.5"), Decimal("2"), "in")
        material_per_unit = Decimal("0.80") * area * Decimal("1.6")
        material_leg = material_per_unit * 100
        # Global ladder seeds 50+ -> 15% off the material leg.
        discount = (material_leg * Decimal("15") / Decimal("100")).quantize(Decimal("0.01"))
        expected = ((Decimal("150") + (material_leg - discount) + Decimal("3") * 100)
                    * product.effective_margin()).quantize(Decimal("0.01"))
        self.assertEqual(quote["total_bdt"], expected)
        self.assertEqual(quote["discount_percent"], Decimal("15"))

    def test_double_sided_costs_more_than_single(self):
        product = make_press_product()
        single = compute_press_quote(product=product, width=1, height=1, quantity=10, sides="4/0")
        double = compute_press_quote(product=product, width=1, height=1, quantity=10, sides="4/4")
        self.assertGreater(double["total_bdt"], single["total_bdt"])

    def test_quote_endpoint_is_public(self):
        product = make_press_product()
        res = APIClient().post("/api/print/press/quote/", {
            "product": product.id, "width": "3.5", "height": "2",
            "unit": "in", "quantity": 100,
        }, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("grand_total_bdt", res.data["data"])


class PressCheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer("presscust")
        self.product = make_press_product()

    def test_checkout_snapshots_price_and_cod_advances(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/print/press/checkout/", {
            "product": self.product.id, "width": "3.5", "height": "2",
            "unit": "in", "quantity": 50, "payment_method": "COD",
            "shipping_zone": "INSIDE_DHAKA_HOME",
            "shipping_address": {"name": "A", "phone": "01", "city": "Dhaka"},
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        order = PressOrder.objects.get()
        self.assertEqual(order.status, PressOrder.Status.ARTWORK_REVIEW)
        self.assertEqual(order.payment_status, "COD_DUE")
        self.assertGreater(order.total_bdt, Decimal("0"))
        self.assertIn("margin_factor", order.price_breakdown)

    def test_customer_cannot_read_another_customers_order(self):
        other = make_customer("other")
        order = PressOrder.objects.create(
            customer=other, product=self.product, size_name="t",
            width=1, height=1, quantity=1, total_bdt=Decimal("10"),
            total_charged=Decimal("10"),
        )
        auth(self.client, self.customer)
        res = self.client.get(f"/api/print/press/orders/{order.pk}/")
        self.assertEqual(res.status_code, 404)

    def test_partial_advance_requires_trusted_corporate(self):
        from printing.models import CorporateAccount

        auth(self.client, self.customer)
        res = self.client.post("/api/print/press/checkout/", {
            "product": self.product.id, "width": "3.5", "height": "2",
            "quantity": 10, "payment_method": "PARTIAL_ADVANCE",
            "shipping_zone": "HUB_PICKUP",
        }, format="json")
        self.assertEqual(res.status_code, 400, res.content)

        CorporateAccount.objects.create(
            customer=self.customer, company_name="Acme Ltd", trusted_for_partial=True,
        )
        res = self.client.post("/api/print/press/checkout/", {
            "product": self.product.id, "width": "3.5", "height": "2",
            "quantity": 10, "payment_method": "PARTIAL_ADVANCE",
            "shipping_zone": "HUB_PICKUP", "is_corporate": True,
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)

    def test_illegal_status_jump_rejected(self):
        staff = make_staff("pressstaff")
        order = PressOrder.objects.create(
            customer=self.customer, product=self.product, size_name="t",
            width=1, height=1, quantity=1, total_bdt=Decimal("10"),
            total_charged=Decimal("10"),
        )
        auth(self.client, staff)
        res = self.client.post(f"/api/print/press/admin/orders/{order.pk}/status/", {
            "status": "DELIVERED",
        }, format="json")
        self.assertEqual(res.status_code, 400, res.content)


class ShowcaseUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = make_staff("showstaff")

    def test_rejects_executable_extension(self):
        auth(self.client, self.staff)
        res = self.client.post("/api/print/admin/showcase/upload/", {
            "file": SimpleUploadedFile("evil.exe", b"MZ", content_type="application/octet-stream"),
        }, format="multipart")
        self.assertEqual(res.status_code, 400, res.content)

    def test_accepts_pdf_and_lists_by_category(self):
        auth(self.client, self.staff)
        res = self.client.post("/api/print/admin/showcase/upload/", {
            "file": SimpleUploadedFile("design.pdf", b"%PDF-1.4", content_type="application/pdf"),
        }, format="multipart")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data["data"]["file_type"], "pdf")

        PrintShowcaseItem.objects.create(
            name="Foil Cards", category="business-cards", file_url=res.data["data"]["file_url"],
            file_type="pdf", badge="HOT", price_bdt=Decimal("450"), is_top_pick=True,
        )
        public = APIClient().get("/api/print/showcase/?category=business-cards&top_picks=1")
        self.assertEqual(public.status_code, 200, public.content)
        names = [it["name"] for it in public.data["data"]]
        self.assertIn("Foil Cards", names)
        mine = [it for it in public.data["data"] if it["name"] == "Foil Cards"][0]
        self.assertEqual(mine["badge"], "HOT")
        self.assertEqual(mine["file_type"], "pdf")
