"""Medicine fields (catalog.models.Products.generic_name/strength/
dosage_form/manufacturer/pack_size/requires_prescription) exposed on the
storefront product serializers, so the UI can show generic name/strength/
manufacturer and a "Prescription required" state. All fields are optional --
the ~200 pre-existing non-medicine products must keep serializing fine with
every one of them blank/False.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products


class MedicineFieldsTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Categories.objects.create(name="Meds", slug="med-cat", description="")


class ExistingProductWithBlankFieldsTests(MedicineFieldsTestBase):
    def test_plain_product_serializes_fine_on_list(self):
        Products.objects.create(
            name="Plain Shirt", slug="med-plain-shirt", sku="MED-PLAIN", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=100, initial_selling_price=200,
        )
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "med-plain-shirt")
        self.assertEqual(row["generic_name"], "")
        self.assertEqual(row["strength"], "")
        self.assertEqual(row["dosage_form"], "")
        self.assertEqual(row["manufacturer"], "")
        self.assertEqual(row["pack_size"], "")
        self.assertFalse(row["requires_prescription"])

    def test_plain_product_serializes_fine_on_detail(self):
        Products.objects.create(
            name="Plain Mug", slug="med-plain-mug", sku="MED-PLAINMUG", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=50, initial_selling_price=90,
        )
        res = self.client.get("/api/store/products/med-plain-mug/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertEqual(data["generic_name"], "")
        self.assertFalse(data["requires_prescription"])


class MedicineProductFieldsTests(MedicineFieldsTestBase):
    def test_medicine_fields_come_through_on_list_and_detail(self):
        Products.objects.create(
            name="Napa Extra", slug="med-napa-extra", sku="MED-NAPA", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=5, initial_selling_price=10,
            generic_name="Paracetamol + Caffeine", strength="500 mg + 65 mg",
            dosage_form="TABLET", manufacturer="Beximco Pharmaceuticals",
            pack_size="10 x 10", requires_prescription=False,
        )
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "med-napa-extra")
        self.assertEqual(row["generic_name"], "Paracetamol + Caffeine")
        self.assertEqual(row["strength"], "500 mg + 65 mg")
        self.assertEqual(row["dosage_form"], "TABLET")
        self.assertEqual(row["manufacturer"], "Beximco Pharmaceuticals")
        self.assertEqual(row["pack_size"], "10 x 10")
        self.assertFalse(row["requires_prescription"])

        res = self.client.get("/api/store/products/med-napa-extra/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["generic_name"], "Paracetamol + Caffeine")

    def test_requires_prescription_flag_is_exposed(self):
        Products.objects.create(
            name="Seclo 20", slug="med-seclo-20", sku="MED-SECLO", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=8, initial_selling_price=15,
            generic_name="Omeprazole", strength="20 mg", dosage_form="CAPSULE",
            manufacturer="Square Pharmaceuticals", requires_prescription=True,
        )
        res = self.client.get("/api/store/products/med-seclo-20/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["data"]["requires_prescription"])
