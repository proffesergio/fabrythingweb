"""Free a username/email held by an account that was never meant to own it.

The case this exists for: a would-be rider signs up at /auth/signup, which only
ever creates `Customer` accounts (riders have no self-serve signup — an admin
creates them from the Riders tab). The person now holds the username and email
the admin needs in order to onboard them properly, and every attempt to add them
as a rider fails with "A user with that email/username already exists."

`prune_orphan_logins` does not help here: it deliberately only prunes Rider and
Restaurant roles, and this account is a Customer.

Deleting a login is not reversible, so the command is built to refuse anything
that looks like it matters:

  * admin/superuser accounts — never
  * accounts that already own a Rider or Restaurant — that is a real staff
    account; deleting the login would orphan the row. Use the admin panel.
  * accounts with order history (food or storefront) — the cascade would take
    the orders with it.

What it will take: the account plus ephemeral signup debris (an empty cart,
notifications, a loyalty account). It always prints the full list first, and
defaults to a dry run.

    python manage.py release_login riderbills            # report only
    python manage.py release_login riderbills --apply    # actually delete
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction
from django.db.models.deletion import Collector

User = get_user_model()

PROTECTED_ROLES = ("Super Admin", "Admin")


class Command(BaseCommand):
    help = "Delete an unused login so its username/email can be reused."

    def add_arguments(self, parser):
        parser.add_argument("identifier", help="Username or email of the account to release.")
        parser.add_argument("--apply", action="store_true",
                            help="Actually delete. Without this it only reports.")

    def handle(self, *args, **options):
        identifier = options["identifier"]

        user = (User.objects.filter(username=identifier).first()
                or User.objects.filter(email__iexact=identifier).first())
        if not user:
            raise CommandError(f"No account with username or email {identifier!r}.")

        self._refuse_if_protected(user)

        self.stdout.write(
            f"Account #{user.id}  {user.role}  {user.username}  {user.email}")
        self.stdout.write("\nDeleting it would also remove:")
        for label, count in self._cascade_summary(user):
            self.stdout.write(f"  {count:>4}  {label}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING(
                "\nDry run — nothing deleted. Re-run with --apply to remove this account."))
            return

        with transaction.atomic():
            user.delete()
        self.stdout.write(self.style.SUCCESS(
            f"\nReleased {identifier!r}. The username and email are free to reuse."))

    def _refuse_if_protected(self, user):
        """Everything here is a reason the operator wants a different tool."""
        if user.is_superuser or user.role in PROTECTED_ROLES:
            raise CommandError(
                f"{user.username!r} is a {user.role} account — refusing to delete it.")

        # OneToOne reverse accessors: Rider.user related_name="rider",
        # Restaurant.owner related_name="restaurant".
        if getattr(user, "rider", None) is not None:
            raise CommandError(
                f"{user.username!r} already owns a Rider row — this is a working rider "
                "account, not a stranded signup. Remove the rider from the admin panel "
                "instead, which deletes both together.")
        if getattr(user, "restaurant", None) is not None:
            raise CommandError(
                f"{user.username!r} owns a Restaurant — remove it from the admin panel "
                "instead.")

        for label, related_name in (("food orders", "food_orders"),
                                    ("storefront orders", "orders")):
            manager = getattr(user, related_name, None)
            if manager is not None and manager.exists():
                raise CommandError(
                    f"{user.username!r} has {manager.count()} {label} — refusing to "
                    "delete, because the cascade would take that history with it.")

    def _cascade_summary(self, user):
        """What Django would actually delete, straight from the collector, so the
        report can never drift from the real cascade."""
        collector = Collector(using=router.db_for_write(User, instance=user))
        collector.collect([user])
        summary = []
        for model, instances in collector.data.items():
            summary.append((model._meta.verbose_name_plural.title(), len(instances)))
        return sorted(summary)
