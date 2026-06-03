from django.core.management.base import BaseCommand
from UserServices.models import Users


class Command(BaseCommand):
    help = "Create a Super Admin user who can log into the admin panel"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Admin username")
        parser.add_argument("--email", required=True, help="Admin email")
        parser.add_argument("--password", required=True, help="Admin password")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if Users.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"Username '{username}' already exists."))
            return

        if Users.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f"Email '{email}' already exists."))
            return

        user = Users.objects.create_user(
            username=username,
            email=email,
            password=password,
            role="Super Admin",
            address="",
            country="Bangladesh",
        )
        # domain_user_id must point to the user themselves — this is what the
        # permission middleware checks to grant full access.
        user.domain_user_id = user
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"\nAdmin user created successfully!"
            f"\n  Username : {username}"
            f"\n  Email    : {email}"
            f"\n  Role     : Super Admin"
            f"\n\nLog in at: http://localhost:3000/admin/auth"
        ))
