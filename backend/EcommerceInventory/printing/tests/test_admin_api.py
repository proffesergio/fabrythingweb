from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from printing.models import PrintArea, PrintPricingConfig, PrintProof, PrintRequest, PrintablePreset
from printing.services import attach_proof, create_print_request
from printing.tests.helpers import auth, make_customer, make_product, make_staff

STAFF_ENDPOINTS = [
    ("get", "/api/print/admin/requests/"),
    ("get", "/api/print/admin/pricing/"),
    ("get", "/api/print/admin/print-areas/"),
    ("get", "/api/print/admin/presets/"),
]


class StaffOnlyAccessTests(TestCase):
    """A Customer role must get 403 on EVERY staff endpoint -- isPlatformScope
    alone would let a self-signed-up customer through (they're their own
    domain root); isPlatformStaff's role check is what must gate this."""

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.request_obj = create_print_request(self.customer, brief="x")

    def test_customer_gets_403_on_list_style_endpoints(self):
        auth(self.client, self.customer)
        for method, url in STAFF_ENDPOINTS:
            res = getattr(self.client, method)(url)
            self.assertEqual(res.status_code, 403, f"{method.upper()} {url} -> {res.status_code}")

    def test_customer_gets_403_on_request_scoped_admin_endpoints(self):
        auth(self.client, self.customer)
        pk = self.request_obj.id
        endpoints = [
            ("get", f"/api/print/admin/requests/{pk}/"),
            ("post", f"/api/print/admin/requests/{pk}/proofs/"),
            ("post", f"/api/print/admin/requests/{pk}/price/"),
            ("post", f"/api/print/admin/requests/{pk}/status/"),
            ("get", f"/api/print/admin/requests/{pk}/export/"),
        ]
        for method, url in endpoints:
            res = getattr(self.client, method)(url, {}, format="json")
            self.assertEqual(res.status_code, 403, f"{method.upper()} {url} -> {res.status_code}")

    def test_unauthenticated_gets_401(self):
        res = self.client.get("/api/print/admin/requests/")
        self.assertEqual(res.status_code, 401)


class AdminQueueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = make_staff()
        self.customer = make_customer()

    def test_queue_lists_all_customers_requests(self):
        r1 = create_print_request(self.customer, brief="job 1")
        other = make_customer("other")
        r2 = create_print_request(other, brief="job 2")
        auth(self.client, self.staff)
        res = self.client.get("/api/print/admin/requests/")
        self.assertEqual(res.status_code, 200)
        ids = {row["id"] for row in res.data["data"]}
        self.assertEqual(ids, {r1.id, r2.id})

    def test_queue_filters_by_status(self):
        r1 = create_print_request(self.customer, brief="job 1")
        r2 = create_print_request(self.customer, brief="job 2")
        r2.transition_to(PrintRequest.Status.IN_DESIGN)

        auth(self.client, self.staff)
        res = self.client.get("/api/print/admin/requests/?status=IN_DESIGN")
        ids = [row["id"] for row in res.data["data"]]
        self.assertEqual(ids, [r2.id])


class AdminProofAndStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = make_staff()
        self.customer = make_customer()
        self.request_obj = create_print_request(self.customer, brief="x")

    def test_attach_proof_via_url(self):
        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/proofs/",
            {"image": "https://cdn.example.com/art.png", "note": "first draft"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, PrintRequest.Status.PROOF_READY)
        self.assertEqual(self.request_obj.proofs.count(), 1)

    def test_attach_proof_via_file_upload(self):
        auth(self.client, self.staff)
        img = SimpleUploadedFile("art.png", b"fake-art-bytes", content_type="image/png")
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/proofs/", {"image": img}, format="multipart",
        )
        self.assertEqual(res.status_code, 201, res.content)
        proof = self.request_obj.proofs.get()
        self.assertTrue(proof.image.startswith("/api/media/"))

    def test_set_price(self):
        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/price/",
            {"unit_price": "450.00"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.quoted_unit_price, Decimal("450.00"))
        self.assertEqual(self.request_obj.quoted_total_price, Decimal("450.00"))

    def test_cannot_reprice_after_approval(self):
        self.request_obj.transition_to(PrintRequest.Status.IN_DESIGN)
        self.request_obj.transition_to(PrintRequest.Status.PROOF_READY)
        self.request_obj.transition_to(PrintRequest.Status.APPROVED)

        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/price/", {"unit_price": "1.00"}, format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_advance_production_status(self):
        self.request_obj.transition_to(PrintRequest.Status.IN_DESIGN)
        self.request_obj.transition_to(PrintRequest.Status.PROOF_READY)
        self.request_obj.transition_to(PrintRequest.Status.APPROVED)

        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/status/", {"status": "IN_PRODUCTION"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, PrintRequest.Status.IN_PRODUCTION)

    def test_illegal_status_jump_rejected_via_api(self):
        auth(self.client, self.staff)
        res = self.client.post(
            f"/api/print/admin/requests/{self.request_obj.id}/status/", {"status": "COMPLETED"}, format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, PrintRequest.Status.SUBMITTED)


class AdminExportTests(TestCase):
    def test_export_returns_artwork_and_spec(self):
        client = APIClient()
        staff = make_staff()
        customer = make_customer()
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("100"))
        area = PrintArea.objects.create(name="Front", price=Decimal("20"))
        pr = create_print_request(
            customer, preset=preset, print_area_ids=[area.id], quantity=2, brief="x",
            roster_lines=[{"player_name": "Alice", "number": "7", "size": "M", "quantity": 1}],
        )
        proof = attach_proof(pr, staff_user=staff, image="https://cdn.example.com/final.png")
        from printing.services import approve_proof
        approve_proof(pr, proof)

        auth(client, staff)
        res = client.get(f"/api/print/admin/requests/{pr.id}/export/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.data["data"]
        self.assertEqual(data["artwork"]["approved_image_url"], "https://cdn.example.com/final.png")
        self.assertEqual(len(data["print_areas"]), 1)
        self.assertEqual(len(data["roster_lines"]), 1)
        self.assertEqual(data["agreed_unit_price"], "120.00")


class AdminConfigCrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = make_staff()

    def test_print_area_crud(self):
        auth(self.client, self.staff)
        res = self.client.post("/api/print/admin/print-areas/", {"name": "Sleeve", "price": "30.00"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        area_id = res.data["data"]["id"]

        res = self.client.patch(f"/api/print/admin/print-areas/{area_id}/", {"price": "35.00"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["price"], "35.00")

        res = self.client.delete(f"/api/print/admin/print-areas/{area_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(PrintArea.objects.count(), 0)

    def test_preset_crud(self):
        product = make_product()
        auth(self.client, self.staff)
        res = self.client.post(
            "/api/print/admin/presets/",
            {"name": "Polo", "base_price": "400.00", "product": product.id}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(PrintablePreset.objects.get().product_id, product.id)

    def test_pricing_config_get_and_update(self):
        auth(self.client, self.staff)
        res = self.client.get("/api/print/admin/pricing/")
        self.assertEqual(res.status_code, 200)

        res = self.client.put(
            "/api/print/admin/pricing/",
            {"quantity_tiers": [{"min_qty": 1, "discount_percent": 0}, {"min_qty": 5, "discount_percent": 20}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        config = PrintPricingConfig.get_solo()
        self.assertEqual(config.discount_percent_for(5), Decimal("20"))
