"""List every back-office (Admin/Super Admin/Staff) account, and delete named
ones after proving they carry no order/content history.

Why this exists: the old public /api/auth/signup/ (see AuthController.py)
handed out "Admin" to anyone who posted to it before today's fix. Production
verification created a real row this way (username __probe_no_create, role
Admin) and there may be others from actual attackers. This command is how the
owner audits and cleans that up from the Render dashboard, which has no shell
on the free plan.

    python manage.py audit_admin_accounts
        Lists every Admin/Super Admin/Staff account (id, role, username,
        email, created_at) so the owner can eyeball which ones are real.

    python manage.py audit_admin_accounts __probe_no_create other_user
        Dry run: for each named account (username or email), prints what
        Django would cascade-delete and a SAFE/REFUSED verdict. Deletes
        nothing.

    python manage.py audit_admin_accounts __probe_no_create --apply
        Deletes only the named accounts that passed the safety check.

Safety check: this app's catalog/purchasing/inventory models point at Users
with on_delete=CASCADE (domain_user_id, added_by_user_id, and friends) -- a
real admin who has been managing products for months would take an entire
catalog down with them if simply deleted. So an account is only ever SAFE to
delete when Django's own deletion Collector shows nothing would cascade
except the account's own bookkeeping rows (UserPermissions, ActivityLog) --
anything else (products, categories, orders, reviews, other user accounts
this one created, ...) refuses the whole command for that account.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction
from django.db.models.deletion import Collector

from core.helpers import PLATFORM_STAFF_ROLES

User = get_user_model()

# Rows that only ever exist BECAUSE this account exists, and describe the
# account itself rather than anything it did on the platform. Safe to take
# along with the account. Everything else in the cascade is "history".
SAFE_CASCADE_MODELS = {"UserPermissions", "ActivityLog"}


class Command(BaseCommand):
    help = "Audit and clean up rogue Admin/Staff/Super Admin accounts (e.g. from the closed public signup hole)."

    def add_arguments(self, parser):
        parser.add_argument(
            "identifiers", nargs="*",
            help="Usernames or emails to consider for deletion. Omit to just list all back-office accounts.")
        parser.add_argument("--apply", action="store_true",
                            help="Actually delete the named accounts that pass the safety check. Without this, only reports.")

    def handle(self, *args, **options):
        identifiers = []
        for raw in options["identifiers"]:
            identifiers.extend(part.strip() for part in raw.split(",") if part.strip())

        if not identifiers:
            self._list_accounts()
            return

        self._audit_and_maybe_delete(identifiers, apply=options["apply"])

    def _list_accounts(self):
        accounts = (User.objects.filter(role__in=PLATFORM_STAFF_ROLES)
                    .order_by("created_at")
                    .values("id", "role", "username", "email", "created_at"))
        accounts = list(accounts)
        if not accounts:
            self.stdout.write("No Admin/Super Admin/Staff accounts exist.")
            return
        self.stdout.write(f"{len(accounts)} back-office account(s):")
        for a in accounts:
            self.stdout.write(
                f"  #{a['id']:<5} {a['role']:<12} {a['username']:<25} {a['email']:<35} created {a['created_at']}")
        self.stdout.write(
            "\nRe-run with one or more usernames/emails to see the deletion "
            "cascade for specific accounts, add --apply to delete the ones that are safe.")

    def _audit_and_maybe_delete(self, identifiers, apply):
        to_delete = []
        for identifier in identifiers:
            user = (User.objects.filter(username=identifier).first()
                    or User.objects.filter(email__iexact=identifier).first())
            if not user:
                self.stdout.write(self.style.ERROR(f"{identifier!r}: no such account."))
                continue

            if user.role not in PLATFORM_STAFF_ROLES:
                self.stdout.write(self.style.ERROR(
                    f"{identifier!r}: role is {user.role!r}, not a back-office role -- "
                    "wrong tool (see release_login/prune_orphan_logins for Customer/Rider/Restaurant)."))
                continue

            verdict, detail = self._safety_verdict(user)
            self.stdout.write(
                f"#{user.id} {user.role} {user.username} ({user.email}), created {user.created_at}")
            for line in detail:
                self.stdout.write(f"    {line}")

            if verdict:
                self.stdout.write(self.style.SUCCESS("  -> SAFE to delete (no order/content history)."))
                to_delete.append(user)
            else:
                self.stdout.write(self.style.ERROR("  -> REFUSED: has order/content history, not deleting."))

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry run -- nothing deleted. Re-run with --apply to delete the accounts marked SAFE."))
            return

        if not to_delete:
            self.stdout.write("\nNothing marked SAFE -- nothing to delete.")
            return

        with transaction.atomic():
            for user in to_delete:
                username = user.username
                user.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {username!r}."))

    def _safety_verdict(self, user):
        """Returns (is_safe, [report lines]) using Django's own deletion
        Collector, so the verdict can never drift from what a real delete
        would actually cascade into."""
        collector = Collector(using=router.db_for_write(User, instance=user))
        collector.collect([user])

        lines = []
        is_safe = True
        for model, instances in collector.data.items():
            count = len(instances)
            label = model._meta.verbose_name_plural.title() if hasattr(model._meta, "verbose_name_plural") else model.__name__
            if model is User:
                # The target itself, plus -- if unsafe -- any OTHER account
                # that would cascade along (e.g. one this admin created, via
                # added_by_user_id/domain_user_id CASCADE).
                others = [i for i in instances if i.pk != user.pk]
                if others:
                    is_safe = False
                    lines.append(f"{len(others)} OTHER user account(s) would cascade-delete too (e.g. accounts it created).")
                continue
            if model.__name__ not in SAFE_CASCADE_MODELS and count:
                is_safe = False
                lines.append(f"{count} {label} row(s) would cascade-delete -- treated as content/history.")
            elif count:
                lines.append(f"{count} {label} row(s) (account bookkeeping, safe).")

        if not lines:
            lines.append("No related rows at all.")
        return is_safe, lines
