"""clear_placeholder_media — see the command docstring for why category rows
still carry loremflickr URLs after purge_demo_catalog ran.

The contracts that matter: it is a dry run unless asked, it never touches a
real image, and it survives the older rows whose `image` is a bare string
rather than a list (a TypeError there would abort a deploy step).
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from catalog.models import Categories

REAL = "https://fabrythingweb.onrender.com/api/media/abc123/"
FILLER = "https://loremflickr.com/600/800/sunglasses?lock=1005"


def make_category(name, slug, image):
    return Categories.objects.create(name=name, slug=slug, description="d", image=image)


def run(*args):
    out = StringIO()
    call_command("clear_placeholder_media", *args, stdout=out)
    return out.getvalue()


class ClearPlaceholderMediaTests(TestCase):
    def test_dry_run_reports_but_writes_nothing(self):
        category = make_category("Eyewear", "eyewear", [FILLER])

        output = run()

        self.assertIn("Eyewear", output)
        self.assertIn("Dry run", output)
        category.refresh_from_db()
        self.assertEqual(category.image, [FILLER])

    def test_apply_clears_the_placeholder(self):
        category = make_category("Eyewear", "eyewear", [FILLER])

        run("--apply")

        category.refresh_from_db()
        self.assertEqual(category.image, [])

    def test_a_real_image_is_never_touched(self):
        category = make_category("Fashion", "fashion", [REAL])

        output = run("--apply")

        self.assertIn("nothing to do", output)
        category.refresh_from_db()
        self.assertEqual(category.image, [REAL])

    def test_a_real_image_alongside_filler_survives(self):
        """Clearing the whole field would throw away real photography that
        happens to share the list with a placeholder."""
        category = make_category("Mixed", "mixed", [REAL, FILLER])

        run("--apply")

        category.refresh_from_db()
        self.assertEqual(category.image, [REAL])

    def test_handles_a_bare_string_image_without_crashing(self):
        """Older rows stored a single URL rather than a list; a TypeError here
        would abort the deploy step this runs in."""
        category = make_category("Legacy", "legacy", FILLER)

        output = run("--apply")

        self.assertIn("Legacy", output)
        category.refresh_from_db()
        self.assertEqual(category.image, [])

    def test_no_placeholders_is_a_clean_no_op(self):
        make_category("Phones", "phones", [])
        self.assertIn("nothing to do", run("--apply"))
