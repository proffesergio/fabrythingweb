"""Delete Rider/Restaurant login accounts that no Rider or Restaurant row points at.

These are created by a half-failed onboarding: the User committed, the object it
belonged to did not. The account is invisible in the admin panel but still owns
its username/email, so retrying the same form fails forever with
"A user with that email/username already exists."

The create paths are atomic now (food/views_food_ext.AdminRiderViewSet.create,
food/services_admin.create_restaurant_with_owner), so this is a one-off repair
for accounts stranded before that fix — not a routine job.

Defaults to a dry run. Pass --apply to actually delete.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()

# Only these roles are safe to prune. A Super Admin/Admin/Customer/Staff account
# is never "orphaned" — it isn't supposed to own a Rider or Restaurant row.
PRUNABLE_ROLES = ("Rider", "Restaurant")


class Command(BaseCommand):
    help = "Remove Rider/Restaurant logins left behind by a failed onboarding."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Actually delete. Without this it only reports.")
        parser.add_argument("--role", choices=PRUNABLE_ROLES,
                            help="Limit to one role (default: both).")

    def handle(self, *args, **options):
        roles = [options["role"]] if options.get("role") else list(PRUNABLE_ROLES)

        # Both are reverse accessors of a OneToOne back to User:
        # Rider.user related_name="rider", Restaurant.owner related_name="restaurant".
        orphans = User.objects.filter(role__in=roles).filter(
            rider__isnull=True, restaurant__isnull=True,
        )

        found = list(orphans.values("id", "username", "email", "role"))
        if not found:
            self.stdout.write(self.style.SUCCESS("No orphan logins found."))
            return

        self.stdout.write(f"Found {len(found)} orphan login(s):")
        for u in found:
            self.stdout.write(f"  #{u['id']:<5} {u['role']:<11} {u['username']:<20} {u['email']}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING(
                "\nDry run — nothing deleted. Re-run with --apply to remove these."))
            return

        with transaction.atomic():
            deleted, _ = User.objects.filter(id__in=[u["id"] for u in found]).delete()
        self.stdout.write(self.style.SUCCESS(f"\nDeleted {len(found)} orphan login(s)."))
