from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodOrder, FoodOrderItem


class FoodOrderModelTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)

    def test_order_code_is_generated_and_unique(self):
        o1 = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                      delivery_address="addr", subtotal=Decimal("100.00"),
                                      delivery_fee=Decimal("20.00"), tip=Decimal("0.00"),
                                      total=Decimal("120.00"))
        o2 = FoodOrder.objects.create(restaurant=self.r, guest_name="B", guest_phone="2",
                                      delivery_address="addr", subtotal=Decimal("50.00"),
                                      delivery_fee=Decimal("20.00"), tip=Decimal("0.00"),
                                      total=Decimal("70.00"))
        self.assertTrue(o1.order_code.startswith("FD-"))
        self.assertNotEqual(o1.order_code, o2.order_code)

    def test_default_status_is_placed(self):
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        self.assertEqual(o.status, FoodOrder.Status.PLACED)

    def test_legal_transition_advances(self):
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        o.transition_to(FoodOrder.Status.CONFIRMED)
        self.assertEqual(o.status, FoodOrder.Status.CONFIRMED)

    def test_illegal_transition_rejected(self):
        from rest_framework.exceptions import ValidationError
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        with self.assertRaises(ValidationError):
            o.transition_to(FoodOrder.Status.DELIVERED)  # cannot skip from PLACED

    def test_order_item_snapshots_line(self):
        o = FoodOrder.objects.create(restaurant=self.r, guest_name="A", guest_phone="1",
                                     delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        it = FoodOrderItem.objects.create(order=o, item=None, item_name="Biriyani",
                                          unit_price=Decimal("120.00"), quantity=2,
                                          selected_options=[{"name": "Large", "price_delta": "50.00"}],
                                          line_total=Decimal("340.00"))
        self.assertEqual(it.item_name, "Biriyani")
        self.assertEqual(o.items.count(), 1)
