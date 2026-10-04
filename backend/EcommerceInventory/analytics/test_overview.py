"""Tests for the modular-admin overview APIs (Shop / Food / notifications).

Auth: APIRequestFactory + force_authenticate with a mock platform user.
IsAnalyticsStaff delegates to core.helpers.isPlatformStaff, which is True
for role='Super Admin' and False for a plain Customer — no DB user needed.
"""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from analytics.views_overview import (FoodOverviewView, NotificationsView,
                                      ShopOverviewView)
from catalog.models import Products, ProductVariant
from food.models import FoodOrder, Restaurant, Rider
from orders.models import Order, OrderItem


def staff():
    return SimpleNamespace(id=1, role="Super Admin",
                           is_authenticated=True, domain_user_id_id=1)


def customer():
    return SimpleNamespace(id=2, role="Customer",
                           is_authenticated=True, domain_user_id_id=2)


def authed(view, user, path):
    req = APIRequestFactory().get(path)
    force_authenticate(req, user=user)
    return view.as_view()(req)


def backdate(model, pk, days):
    model.objects.filter(pk=pk).update(
        created_at=timezone.now() - timedelta(days=days))


class ShopOverviewTests(TestCase):
    def setUp(self):
        o1 = Order.objects.create(
            status=Order.Status.DELIVERED, subtotal=Decimal("450.00"),
            shipping_amount=Decimal("50.00"), total_amount=Decimal("500.00"),
            contact_name="A", contact_phone="01", shipping_address={})
        OrderItem.objects.create(
            order=o1, product_name="Shirt", sku="S1",
            unit_price=Decimal("250.00"), quantity=2,
            line_total=Decimal("500.00"))
        o2 = Order.objects.create(
            status=Order.Status.CANCELED, subtotal=Decimal("100.00"),
            shipping_amount=Decimal("0.00"), total_amount=Decimal("100.00"),
            contact_name="B", contact_phone="02", shipping_address={})
        backdate(Order, o2.pk, 10)  # prior window, and canceled anyway
        p = Products.objects.create(
            description="d", sku="T1", initial_buying_price=10.0,
            initial_selling_price=20.0)
        ProductVariant.objects.create(
            product=p, sku="V1", size="S", price=Decimal("20.00"),
            stock_quantity=3)
        ProductVariant.objects.create(
            product=p, sku="V2", size="M", price=Decimal("20.00"),
            stock_quantity=0)

    def test_kpis_series_top_recent_alerts(self):
        r = authed(ShopOverviewView, staff(),
                   "/api/store/analytics/admin/shop-overview/")
        assert r.status_code == 200, r.data
        d = r.data["data"]
        assert d["kpis"]["revenue_7d"] == 500.0
        assert d["kpis"]["orders_7d"] == 1
        assert d["kpis"]["avg_order_value"] == 500.0
        assert len(d["series"]) == 14
        assert d["top_products"][0]["name"] == "Shirt"
        assert d["top_products"][0]["qty"] == 2
        assert d["recent_orders"][0]["order_number"]
        assert d["alerts"]["low_stock"] == 2  # qty 3 + qty 0 (also <= 5)
        assert d["alerts"]["out_of_stock"] == 1

    def test_days_param(self):
        r = authed(ShopOverviewView, staff(),
                   "/api/store/analytics/admin/shop-overview/?days=30")
        assert len(r.data["data"]["series"]) == 30

    def test_forbidden_for_customer(self):
        r = authed(ShopOverviewView, customer(),
                   "/api/store/analytics/admin/shop-overview/")
        assert r.status_code == 403


class FoodOverviewTests(TestCase):
    def setUp(self):
        self.rest = Restaurant.objects.create(
            name="R1", slug="r1", status="ACTIVE")
        Restaurant.objects.create(name="R2", slug="r2", status="PENDING")
        FoodOrder.objects.create(
            guest_name="G", guest_phone="01", delivery_address="D",
            restaurant=self.rest, subtotal=Decimal("200.00"),
            total=Decimal("200.00"), status=FoodOrder.Status.DELIVERED,
            payment_status="PENDING")
        Rider.objects.create(name="Rider1", last_seen_at=timezone.now())

    def test_kpis_alerts(self):
        r = authed(FoodOverviewView, staff(),
                   "/api/store/analytics/admin/food-overview/")
        assert r.status_code == 200, r.data
        d = r.data["data"]
        assert d["kpis"]["gmv_7d"] == 200.0
        assert d["kpis"]["orders_7d"] == 1
        assert d["kpis"]["active_restaurants"] == 1
        assert d["kpis"]["online_riders"] == 1
        assert d["top_restaurants"][0]["name"] == "R1"
        assert d["alerts"]["pending_partners"] == 1
        assert d["alerts"]["cash_to_collect"] == 200.0

    def test_forbidden_for_customer(self):
        r = authed(FoodOverviewView, customer(),
                   "/api/store/analytics/admin/food-overview/")
        assert r.status_code == 403


class NotificationsTests(TestCase):
    def test_rollup_shape(self):
        r = authed(NotificationsView, staff(),
                   "/api/store/analytics/admin/notifications/")
        assert r.status_code == 200, r.data
        d = r.data["data"]
        assert set(d) == {"shop", "food", "news", "total"}
        assert d["total"] == (sum(d["shop"].values()) + sum(d["food"].values())
                              + sum(d["news"].values()))

    def test_forbidden_for_customer(self):
        r = authed(NotificationsView, customer(),
                   "/api/store/analytics/admin/notifications/")
        assert r.status_code == 403


class ModuleTagSeedTests(TestCase):
    def test_seed_tags_businesses(self):
        from django.core.management import call_command
        from accounts.models import Modules
        call_command("seed_admin_modules")
        by_name = {m.module_name: m.module for m in Modules.objects.all()}
        assert by_name["NobleSeek News"] == "news"
        assert by_name["Food"] == "food"
        assert by_name["Products"] == "shop"
        assert by_name["Settings"] == "shared"
        # children inherit the parent business
        assert by_name["Food Orders"] == "food"
        assert by_name["All Products"] == "shop"
