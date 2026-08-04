from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from printing.models import PrintArea, PrintRequest, PrintablePreset
from printing.services import attach_proof, create_print_request
from printing.tests.helpers import auth, make_customer, make_staff


class PrintRequestSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()

    def test_submit_creates_request_and_chat_thread(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/print/requests/",
            {"brief": "Team jersey with player names", "quantity": 3, "color": "Red"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(PrintRequest.objects.count(), 1)
        pr = PrintRequest.objects.get()
        self.assertEqual(pr.customer_id, self.customer.id)
        self.assertEqual(pr.status, PrintRequest.Status.SUBMITTED)
        self.assertIsNotNone(pr.chat_thread_id)
        self.assertEqual(pr.chat_thread.kind, "PRINT_JOB")
        self.assertEqual(pr.chat_thread.related_kind, "printing.PrintRequest")
        self.assertEqual(pr.chat_thread.related_id, pr.id)
        self.assertEqual(pr.chat_thread.messages.count(), 1)

    def test_submit_with_roster_lines(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/print/requests/",
            {
                "brief": "Team order", "quantity": 2,
                "roster_lines": [
                    {"player_name": "Alice", "number": "7", "size": "M", "quantity": 1},
                    {"player_name": "Bob", "number": "10", "size": "L", "quantity": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        pr = PrintRequest.objects.get()
        self.assertEqual(pr.roster_lines.count(), 2)

    def test_submit_rejects_blank_brief(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/print/requests/", {"brief": "", "quantity": 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(PrintRequest.objects.count(), 0)

    def test_submit_rejects_unknown_print_area(self):
        auth(self.client, self.customer)
        res = self.client.post(
            "/api/print/requests/", {"brief": "x", "quantity": 1, "print_areas": [999]}, format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_submit_requires_auth(self):
        res = self.client.post("/api/print/requests/", {"brief": "x", "quantity": 1}, format="json")
        self.assertEqual(res.status_code, 401)


class PrintRequestScopingTests(TestCase):
    """A customer may only ever read or act on their OWN print requests."""

    def setUp(self):
        self.client = APIClient()
        self.owner = make_customer("owner")
        self.other = make_customer("other")
        self.request_obj = create_print_request(self.owner, brief="Owner's job", quantity=1)

    def test_list_only_shows_own_requests(self):
        create_print_request(self.other, brief="Other's job")
        auth(self.client, self.owner)
        res = self.client.get("/api/print/requests/")
        self.assertEqual(res.status_code, 200)
        ids = {row["id"] for row in res.data["data"]}
        self.assertEqual(ids, {self.request_obj.id})

    def test_owner_can_read_own_detail(self):
        auth(self.client, self.owner)
        res = self.client.get(f"/api/print/requests/{self.request_obj.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["id"], self.request_obj.id)

    def test_other_customer_cannot_read_detail(self):
        auth(self.client, self.other)
        res = self.client.get(f"/api/print/requests/{self.request_obj.id}/")
        self.assertEqual(res.status_code, 404)

    def test_other_customer_cannot_upload_reference_image(self):
        auth(self.client, self.other)
        img = SimpleUploadedFile("ref.png", b"fake-bytes", content_type="image/png")
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/reference-images/", {"image": img}, format="multipart",
        )
        self.assertEqual(res.status_code, 404)

    def test_other_customer_cannot_add_roster_line(self):
        auth(self.client, self.other)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/roster/",
            {"player_name": "Intruder", "size": "M", "quantity": 1}, format="json",
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.request_obj.roster_lines.count(), 0)

    def test_other_customer_cannot_decide_proof(self):
        staff = make_staff()
        proof = attach_proof(self.request_obj, staff_user=staff, image="https://x/1.png")
        auth(self.client, self.other)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/proofs/{proof.id}/decision/",
            {"decision": "APPROVED"}, format="json",
        )
        self.assertEqual(res.status_code, 404)
        proof.refresh_from_db()
        self.assertEqual(proof.decision, "PENDING")


class ReferenceImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.request_obj = create_print_request(self.customer, brief="x")

    def test_upload_appends_url(self):
        auth(self.client, self.customer)
        img = SimpleUploadedFile("ref.png", b"fake-bytes", content_type="image/png")
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/reference-images/", {"image": img}, format="multipart",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(len(self.request_obj.reference_images), 1)
        self.assertTrue(self.request_obj.reference_images[0].startswith("/api/media/"))


class RosterLineCrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.request_obj = create_print_request(self.customer, brief="x")

    def test_add_update_delete_roster_line(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/roster/",
            {"player_name": "Alice", "number": "7", "size": "M", "quantity": 1}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        line_id = res.data["data"]["id"]

        res = self.client.patch(
            f"/api/print/requests/{self.request_obj.id}/roster/{line_id}/", {"number": "99"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["number"], "99")

        res = self.client.delete(f"/api/print/requests/{self.request_obj.id}/roster/{line_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.request_obj.roster_lines.count(), 0)

    def test_roster_locked_after_approval(self):
        self.request_obj.transition_to(PrintRequest.Status.IN_DESIGN)
        self.request_obj.transition_to(PrintRequest.Status.PROOF_READY)
        self.request_obj.transition_to(PrintRequest.Status.APPROVED)

        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/roster/",
            {"player_name": "Alice", "size": "M", "quantity": 1}, format="json",
        )
        self.assertEqual(res.status_code, 400)


class ProofDecisionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.staff = make_staff()
        self.preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("300"))
        self.request_obj = create_print_request(self.customer, preset=self.preset, quantity=2, brief="x")
        self.proof = attach_proof(self.request_obj, staff_user=self.staff, image="https://x/1.png")

    def test_approve_proof_snapshots_price(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/proofs/{self.proof.id}/decision/",
            {"decision": "APPROVED"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, PrintRequest.Status.APPROVED)
        self.assertEqual(self.request_obj.agreed_unit_price, Decimal("300"))
        self.assertEqual(self.request_obj.agreed_total_price, Decimal("600"))

    def test_request_revision_requires_feedback(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/proofs/{self.proof.id}/decision/",
            {"decision": "REVISION_REQUESTED"}, format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_request_revision_creates_new_proof_round(self):
        auth(self.client, self.customer)
        res = self.client.post(
            f"/api/print/requests/{self.request_obj.id}/proofs/{self.proof.id}/decision/",
            {"decision": "REVISION_REQUESTED", "feedback": "Bigger logo please"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, PrintRequest.Status.REVISION_REQUESTED)

        attach_proof(self.request_obj, staff_user=self.staff, image="https://x/2.png")
        self.assertEqual(self.request_obj.proofs.count(), 2)


class PublicCatalogEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_presets_and_areas_are_public(self):
        PrintablePreset.objects.create(name="Tee", base_price=Decimal("300"), is_active=True)
        PrintArea.objects.update_or_create(
            name="Front", defaults={"price": Decimal("50"), "is_active": True})
        # Seeded reference rows exist too, so assert the endpoint is public
        # and includes what this test created — not an exact table count.
        res = self.client.get("/api/print/presets/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Tee", [p["name"] for p in res.data["data"]])
        res = self.client.get("/api/print/print-areas/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Front", [a["name"] for a in res.data["data"]])

    def test_quote_endpoint_is_public_and_matches_service(self):
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("300"))
        res = self.client.post("/api/print/quote/", {"preset": preset.id, "quantity": 1}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["data"]["unit_price"], "300.00")
