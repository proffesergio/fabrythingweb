"""CreatePurchaseOrderView was IsAuthenticated only, with no role check --
any authenticated Customer could POST /api/orders/purchaseOrder/ and create
real PurchaseOrder/PurchaseOrderItems/PurchaseOrderLogs rows stamped with
their own domain_user_id, no existing row required first (unlike the
warehouse/dynamic-form writes, which need a pre-existing own-domain row).
Gated on the role axis (core.helpers.PLATFORM_STAFF_ROLES) -- see
accounts/controllers/UserController.py for the identical pattern and why it
isn't the full isPlatformStaff predicate (both branches here already scope
by the caller's own domain, so a legitimate non-root Staff account must keep
creating purchase orders for its own tenant).
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Users
from catalog.models import Categories, Products
from inventory.models import Warehouse
from purchasing.controllers.PurchaseOrderController import CreatePurchaseOrderView
from purchasing.models import PurchaseOrder


def make_po_payload(warehouse, supplier, product):
    return {
        "warehouse_id": warehouse.id,
        "supplier_id": supplier.id,
        "po_code": "PO-AUTH-TEST-1",
        "po_date": "2026-01-01T00:00:00Z",
        "expected_delivery_date": "2026-01-05T00:00:00Z",
        "status": "DRAFT",
        "additional_details": {},
        "items": [
            {"product_id": product.id, "quantity_ordered": 5, "additional_details": {}},
        ],
    }


class PurchaseOrderAuthorizationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = Users.objects.create_user(
            username="po-admin", email="po-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="po-customer", email="po-customer@x.com", password="x",
            role="Customer", country="Bangladesh")
        self.supplier = Users.objects.create_user(
            username="po-supplier", email="po-supplier@x.com", password="x",
            role="Supplier", country="Bangladesh")
        self.warehouse = Warehouse.objects.create(
            name="PO Warehouse", address="1 Road", city="Dhaka", state="Dhaka",
            country="Bangladesh", pincode="1200", phone="0100000000",
            email="po-wh@x.com", additional_details={},
            domain_user_id=self.admin, added_by_user_id=self.admin,
            warehouse_manager=self.admin)
        cat = Categories.objects.create(name="PO Cat", slug="po-cat", description="")
        self.product = Products.objects.create(
            name="PO Product", slug="po-product", sku="PO-0001",
            category_id=cat, status="ACTIVE", description="",
            initial_buying_price=10, initial_selling_price=20,
            domain_user_id=self.admin, added_by_user_id=self.admin)

    def _post(self, user, data):
        request = self.factory.post("/api/orders/purchaseOrder/", data, format="json")
        force_authenticate(request, user=user)
        return CreatePurchaseOrderView.as_view()(request)

    def _get(self, user):
        request = self.factory.get("/api/orders/purchaseOrder/")
        force_authenticate(request, user=user)
        return CreatePurchaseOrderView.as_view()(request)

    def test_customer_forbidden_from_creating_purchase_order(self):
        res = self._post(self.customer, make_po_payload(self.warehouse, self.supplier, self.product))
        self.assertEqual(res.status_code, 403)
        self.assertFalse(PurchaseOrder.objects.filter(po_code="PO-AUTH-TEST-1").exists())

    def test_customer_forbidden_from_blank_create_form(self):
        res = self._get(self.customer)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_still_fetch_blank_create_form(self):
        res = self._get(self.admin)
        self.assertEqual(res.status_code, 200)

    def test_admin_can_still_create_purchase_order(self):
        res = self._post(self.admin, make_po_payload(self.warehouse, self.supplier, self.product))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(PurchaseOrder.objects.filter(po_code="PO-AUTH-TEST-1").exists())
