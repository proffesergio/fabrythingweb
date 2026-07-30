"""Write-path helpers for the print-on-demand proof/revision loop.

Every state-changing action a view performs (create a request, attach a
proof, decide on a proof, adjust price) goes through here rather than
manipulating models directly in the view, so the chat-thread system message
and the PrintRequest.transition_to() choke point are never bypassed by a
future endpoint.
"""
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from printing.models import PrintPricingConfig, PrintProof, PrintRequest, PrintRosterLine


def compute_quote(print_request=None, *, preset=None, print_areas=None, quantity=None):
    """Garment base price + per-print-area charge, times quantity, less the
    quantity-tier discount. Callable either with a saved PrintRequest (reads
    its preset/print_areas/quantity) or with raw inputs (for a pre-submit
    live quote where nothing is saved yet).
    """
    if print_request is not None:
        preset = print_request.preset
        print_areas = list(print_request.print_areas.all())
        quantity = print_request.quantity

    quantity = quantity or 1
    garment_price = preset.base_price if preset else Decimal("0")
    areas_total = sum((area.price for area in (print_areas or [])), Decimal("0"))
    unit_price = Decimal(garment_price) + areas_total

    config = PrintPricingConfig.get_solo()
    discount_percent = config.discount_percent_for(quantity)

    subtotal = unit_price * quantity
    discount_amount = (subtotal * discount_percent / Decimal("100")).quantize(Decimal("0.01"))
    total_price = subtotal - discount_amount

    return {
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "total_price": total_price,
    }


def _post_system_message(thread, body):
    """Best-effort SYSTEM chat message -- never lets a chat hiccup fail the
    print-request action that triggered it (same guarantee
    chat.services.notify_admin_of_customer_message makes for its own,
    unrelated, failure mode)."""
    if thread is None:
        return
    try:
        from chat.services import post_message
        from chat.models import ChatMessage

        post_message(thread, sender=None, sender_role=ChatMessage.SenderRole.SYSTEM, body=body)
    except Exception:
        import logging

        logging.getLogger("printing.services").exception(
            "printing: failed to post system chat message for thread %s", thread.pk if thread else None,
        )


@transaction.atomic
def create_print_request(customer, *, product=None, preset=None, color="", size="", quantity=1,
                          brief="", reference_images=None, print_area_ids=None, roster_lines=None):
    """Create a PrintRequest and its own PRINT_JOB chat thread in one go --
    a request with no way to discuss revisions is not a useful state to
    expose (mirrors chat.views.ChatThreadListCreateView.post, which opens a
    thread with its first message together rather than as two calls)."""
    from chat.models import ChatThread

    print_request = PrintRequest.objects.create(
        customer=customer,
        product=product or (preset.product if preset else None),
        preset=preset,
        color=color,
        size=size,
        quantity=quantity,
        brief=brief,
        reference_images=list(reference_images or []),
    )
    if print_area_ids:
        print_request.print_areas.set(print_area_ids)

    for line in (roster_lines or []):
        PrintRosterLine.objects.create(print_request=print_request, **line)

    thread = ChatThread.objects.create(
        customer=customer,
        kind=ChatThread.Kind.PRINT_JOB,
        related_kind="printing.PrintRequest",
        related_id=print_request.id,
    )
    print_request.chat_thread = thread
    print_request.save(update_fields=["chat_thread", "updated_at"])
    _post_system_message(thread, "Custom print request submitted. We'll start on your design shortly.")
    return print_request


def attach_proof(print_request, *, staff_user, image, note=""):
    """Owner attaches a new artwork version. Auto-advances the request
    through IN_DESIGN if it isn't there yet (from SUBMITTED or a fresh
    REVISION_REQUESTED loop), then to PROOF_READY -- so staff only has to
    call this one action rather than choreograph two status calls."""
    if print_request.status not in (
        PrintRequest.Status.IN_DESIGN, PrintRequest.Status.SUBMITTED, PrintRequest.Status.REVISION_REQUESTED,
    ):
        raise ValidationError(f"Cannot attach a proof while request is {print_request.status}.")

    if print_request.status != PrintRequest.Status.IN_DESIGN:
        print_request.transition_to(PrintRequest.Status.IN_DESIGN)

    next_version = (print_request.proofs.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    proof = PrintProof.objects.create(
        print_request=print_request, image=image, version=next_version, note=note, created_by=staff_user,
    )
    print_request.transition_to(PrintRequest.Status.PROOF_READY)
    _post_system_message(
        print_request.chat_thread,
        f"New proof attached (v{proof.version}). Please review and approve or request a revision.",
    )
    return proof


def _latest_pending_proof(print_request):
    proof = print_request.proofs.order_by("-version").first()
    if proof is None or proof.decision != PrintProof.Decision.PENDING:
        raise ValidationError("There is no pending proof to decide on.")
    return proof


def approve_proof(print_request, proof):
    from django.utils import timezone

    latest = _latest_pending_proof(print_request)
    if latest.pk != proof.pk:
        raise ValidationError("Only the latest proof can be approved.")

    proof.decision = PrintProof.Decision.APPROVED
    proof.decided_at = timezone.now()
    proof.save(update_fields=["decision", "decided_at", "updated_at"])

    print_request.transition_to(PrintRequest.Status.APPROVED)
    _post_system_message(print_request.chat_thread, f"Proof v{proof.version} approved. Price locked in.")
    return proof


def request_revision(print_request, proof, *, feedback):
    from django.utils import timezone

    if not feedback or not feedback.strip():
        raise ValidationError("Feedback is required when requesting a revision.")

    latest = _latest_pending_proof(print_request)
    if latest.pk != proof.pk:
        raise ValidationError("Only the latest proof can have a revision requested.")

    proof.decision = PrintProof.Decision.REVISION_REQUESTED
    proof.customer_feedback = feedback
    proof.decided_at = timezone.now()
    proof.save(update_fields=["decision", "customer_feedback", "decided_at", "updated_at"])

    print_request.transition_to(PrintRequest.Status.REVISION_REQUESTED)
    _post_system_message(
        print_request.chat_thread, f"Revision requested on proof v{proof.version}: {feedback}",
    )
    return proof


def set_price(print_request, *, unit_price, total_price=None):
    if print_request.status not in (
        PrintRequest.Status.SUBMITTED, PrintRequest.Status.IN_DESIGN,
        PrintRequest.Status.PROOF_READY, PrintRequest.Status.REVISION_REQUESTED,
    ):
        raise ValidationError("Cannot change price once a request is approved or later.")

    print_request.quoted_unit_price = unit_price
    print_request.quoted_total_price = total_price if total_price is not None else unit_price * print_request.quantity
    print_request.save(update_fields=["quoted_unit_price", "quoted_total_price", "updated_at"])
    return print_request
