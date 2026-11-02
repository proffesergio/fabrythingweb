"""Expire timed-out delivery offers and cascade stuck orders to the next rider.

The offer cycle is normally kept moving by riders polling their dashboards
(RiderOfferView sweeps on every poll). This command is the backstop for the case
where the rider an offer went to has closed their tab and stopped polling, so
nothing else would notice the timeout. Safe to run on a short cron (every
minute) where one is available; idempotent, and a no-op when nothing is stuck.
"""
from django.core.management.base import BaseCommand

from food.services_dispatch import sweep_offers


class Command(BaseCommand):
    help = "Expire timed-out delivery offers and re-offer stuck orders."

    def handle(self, *args, **options):
        expired, re_offered = sweep_offers()
        self.stdout.write(f"Expired {expired} offer(s); re-offered {re_offered} order(s).")
