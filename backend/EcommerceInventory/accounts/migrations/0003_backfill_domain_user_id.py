"""Backfill `domain_user_id` for accounts created before Users.save() self-healed it.

Every user created in one shot (`create_user()` / `objects.create()`) was left with
domain_user_id NULL, because the old self-heal ran before the INSERT assigned an id.
`PermissionMiddleware` and `SidebarController` dereference `user.domain_user_id.id`
unconditionally, so those accounts got a blank 500 on /api/getMenus/ and on every
permission-gated /api/ route — which is what took the rider logins down.

The model fix stops new rows going in broken; this repairs the ones already there.
Idempotent: only touches rows that are still NULL.
"""

from django.db import migrations, models


def backfill(apps, schema_editor):
    Users = apps.get_model("accounts", "Users")
    Users.objects.filter(domain_user_id__isnull=True).update(
        domain_user_id=models.F("id")
    )


def noop(apps, schema_editor):
    """Deliberately a no-op in reverse: we cannot tell which rows were NULL before,
    and restoring NULLs would re-break the accounts this repaired."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_users_role"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
