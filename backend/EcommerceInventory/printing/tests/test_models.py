from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from printing.models import PrintArea, PrintPricingConfig, PrintProof, PrintRequest, PrintablePreset
from printing.services import attach_proof, approve_proof, compute_quote, create_print_request, request_revision
from printing.tests.helpers import make_customer, make_staff


class StatusTransitionTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.request = create_print_request(self.customer, brief="Team jersey", quantity=1)

    def test_legal_forward_chain(self):
        r = self.request
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        self.assertEqual(r.status, PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        r.transition_to(PrintRequest.Status.APPROVED)
        self.assertEqual(r.status, PrintRequest.Status.APPROVED)
        self.assertIsNotNone(r.approved_at)
        r.transition_to(PrintRequest.Status.IN_PRODUCTION)
        r.transition_to(PrintRequest.Status.READY)
        r.transition_to(PrintRequest.Status.COMPLETED)
        self.assertEqual(r.status, PrintRequest.Status.COMPLETED)

    def test_revision_loop(self):
        r = self.request
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        r.transition_to(PrintRequest.Status.REVISION_REQUESTED)
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        self.assertEqual(r.status, PrintRequest.Status.PROOF_READY)

    def test_illegal_transition_rejected(self):
        r = self.request
        with self.assertRaises(ValidationError):
            r.transition_to(PrintRequest.Status.APPROVED)  # SUBMITTED -> APPROVED skips design/proof
        r.refresh_from_db()
        self.assertEqual(r.status, PrintRequest.Status.SUBMITTED)

    def test_illegal_transition_from_terminal_state(self):
        r = self.request
        r.transition_to(PrintRequest.Status.CANCELLED)
        with self.assertRaises(ValidationError):
            r.transition_to(PrintRequest.Status.IN_DESIGN)

    def test_same_status_is_a_noop(self):
        r = self.request
        result = r.transition_to(PrintRequest.Status.SUBMITTED)
        self.assertEqual(result.status, PrintRequest.Status.SUBMITTED)

    def test_approval_snapshots_quoted_price(self):
        r = self.request
        r.quoted_unit_price = Decimal("500.00")
        r.quoted_total_price = Decimal("500.00")
        r.save()
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        r.transition_to(PrintRequest.Status.APPROVED)
        self.assertEqual(r.agreed_unit_price, Decimal("500.00"))
        self.assertEqual(r.agreed_total_price, Decimal("500.00"))

    def test_approval_falls_back_to_computed_quote_if_never_priced(self):
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("300"))
        area, _ = PrintArea.objects.update_or_create(name="Front", defaults={"price": Decimal("50")})
        r = create_print_request(self.customer, preset=preset, print_area_ids=[area.id], quantity=2, brief="x")
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        r.transition_to(PrintRequest.Status.APPROVED)
        # unit = 300 + 50 = 350; qty 2 -> subtotal 700, no tier discount below 10
        self.assertEqual(r.agreed_unit_price, Decimal("350"))
        self.assertEqual(r.agreed_total_price, Decimal("700"))

    def test_config_change_after_approval_never_moves_agreed_price(self):
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("300"))
        r = create_print_request(self.customer, preset=preset, quantity=1, brief="x")
        r.transition_to(PrintRequest.Status.IN_DESIGN)
        r.transition_to(PrintRequest.Status.PROOF_READY)
        r.transition_to(PrintRequest.Status.APPROVED)
        agreed = r.agreed_unit_price

        preset.base_price = Decimal("999")
        preset.save()

        r.refresh_from_db()
        self.assertEqual(r.agreed_unit_price, agreed)


class ProofVersioningTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.staff = make_staff()
        self.request = create_print_request(self.customer, brief="Logo tee")

    def test_attach_proof_advances_status_and_versions(self):
        proof1 = attach_proof(self.request, staff_user=self.staff, image="https://x/1.png", note="v1")
        self.request.refresh_from_db()
        self.assertEqual(proof1.version, 1)
        self.assertEqual(self.request.status, PrintRequest.Status.PROOF_READY)

    def test_revision_round_creates_new_proof_version(self):
        proof1 = attach_proof(self.request, staff_user=self.staff, image="https://x/1.png")
        self.request.refresh_from_db()
        request_revision(self.request, proof1, feedback="Make the logo bigger")
        self.request.refresh_from_db()
        proof1.refresh_from_db()
        self.assertEqual(proof1.decision, PrintProof.Decision.REVISION_REQUESTED)
        self.assertEqual(proof1.customer_feedback, "Make the logo bigger")
        self.assertEqual(self.request.status, PrintRequest.Status.REVISION_REQUESTED)

        proof2 = attach_proof(self.request, staff_user=self.staff, image="https://x/2.png", note="v2")
        self.assertEqual(proof2.version, 2)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PrintRequest.Status.PROOF_READY)
        self.assertEqual(self.request.proofs.count(), 2)

    def test_revision_requires_feedback(self):
        proof1 = attach_proof(self.request, staff_user=self.staff, image="https://x/1.png")
        with self.assertRaises(ValidationError):
            request_revision(self.request, proof1, feedback="   ")

    def test_only_latest_proof_can_be_decided(self):
        proof1 = attach_proof(self.request, staff_user=self.staff, image="https://x/1.png")
        request_revision(self.request, proof1, feedback="bigger logo")
        proof2 = attach_proof(self.request, staff_user=self.staff, image="https://x/2.png")
        with self.assertRaises(ValidationError):
            approve_proof(self.request, proof1)  # stale proof, not the latest
        # latest still decides fine
        approve_proof(self.request, proof2)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PrintRequest.Status.APPROVED)


class PricingTests(TestCase):
    def test_quantity_tier_discount_applied(self):
        config = PrintPricingConfig.get_solo()
        config.quantity_tiers = [
            {"min_qty": 1, "discount_percent": 0},
            {"min_qty": 10, "discount_percent": 10},
        ]
        config.save()
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("100"))
        quote = compute_quote(preset=preset, print_areas=[], quantity=10)
        self.assertEqual(quote["unit_price"], Decimal("100"))
        self.assertEqual(quote["subtotal"], Decimal("1000"))
        self.assertEqual(quote["discount_percent"], Decimal("10"))
        self.assertEqual(quote["total_price"], Decimal("900.00"))

    def test_below_tier_threshold_gets_no_discount(self):
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("100"))
        quote = compute_quote(preset=preset, print_areas=[], quantity=1)
        self.assertEqual(quote["discount_percent"], Decimal("0"))
        self.assertEqual(quote["total_price"], Decimal("100"))

    def test_print_areas_add_to_unit_price(self):
        preset = PrintablePreset.objects.create(name="Tee", base_price=Decimal("100"))
        front, _ = PrintArea.objects.update_or_create(name="Front", defaults={"price": Decimal("50")})
        back, _ = PrintArea.objects.update_or_create(name="Back", defaults={"price": Decimal("70")})
        quote = compute_quote(preset=preset, print_areas=[front, back], quantity=1)
        self.assertEqual(quote["unit_price"], Decimal("220"))

    def test_no_preset_defaults_garment_price_to_zero(self):
        quote = compute_quote(preset=None, print_areas=[], quantity=1)
        self.assertEqual(quote["unit_price"], Decimal("0"))


class RosterLineTests(TestCase):
    def test_roster_lines_belong_to_their_request(self):
        customer = make_customer()
        r1 = create_print_request(
            customer, brief="Team A", roster_lines=[{"player_name": "Alice", "number": "7", "size": "M", "quantity": 1}],
        )
        r2 = create_print_request(customer, brief="Team B")
        self.assertEqual(r1.roster_lines.count(), 1)
        self.assertEqual(r2.roster_lines.count(), 0)
        line = r1.roster_lines.get()
        self.assertEqual(line.print_request_id, r1.id)
        self.assertEqual(line.player_name, "Alice")
