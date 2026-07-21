"""Seed delivery coverage for Bancharampur Upazila (Brahmanbaria, Bangladesh).

Creates the 13 union parishads as DeliveryZones and their villages (121 total,
source: Wikipedia "Bancharampur Upazila"). Union-level Bangla names are provided;
village Bangla names are left blank and fall back to English in the UI until an
admin fills them in.

Coordinates are approximate union centres inside the upazila bounding box
(~23.70–23.86 N, 90.73–90.85 E); the customer's precise spot comes from the map
pin at checkout, so a rough centre only seeds where the map opens.

Usage:
    python manage.py seed_bancharampur              # create/update the 13 unions + villages
    python manage.py seed_bancharampur --exclusive  # also deactivate every other zone
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from food.models import DeliveryZone, Village

# (english, bangla, lat, lng, [villages...])
UNIONS = [
    ("Pahariakandi", "পাহাড়িয়াকান্দি", "23.8200", "90.8000", [
        "Joykalipur", "Nabipur", "Domrakandi", "Ulokandi", "Barokandi",
        "Kalakandi", "Hijlakandi", "Pahariakandi", "Munshinagar"]),
    ("Saifullakandi", "সাইফুল্লাকান্দি", "23.8100", "90.7700", [
        "Vhelanagar", "Darivhelanagar", "Fatapur", "Baluakandi", "Sarifpur",
        "Paratuli", "Kanchanpur", "Moddonagar", "Domrakandi", "Saifullakandi",
        "Mangolhati", "Machimnagar"]),
    ("Darikandi", "দরিকান্দি", "23.8000", "90.8300", [
        "Khalla", "Krisnonagar", "Bahadurpor", "Darikandi", "Darigou",
        "Gokolnagar", "Gopalnagar", "Imamnagar", "Gibongonj"]),
    ("Rupasdi", "রূপসদী", "23.7900", "90.7500", [
        "Rupasdi", "Hoglakandi", "Kawarpur"]),
    ("Farhabad", "ফরদাবাদ", "23.7850", "90.8200", [
        "Fardabad", "Nijkandi", "Gaouratuli", "Tilokkandi", "Purbohati",
        "Kalakandi", "Charlahania"]),
    ("Tezkhali", "তেজখালী", "23.7750", "90.7600", [
        "Joynagar", "Imamnagar", "Akanagar", "Gotkandi", "Horinagar",
        "Bishnorampur", "Baherchor", "Tezkhali", "Hasonnagar"]),
    ("Dariadulat", "দরিয়াদৌলত", "23.7700", "90.8100", [
        "Moricahkandi", "Bakhornagar", "Noton Kodomtuli", "Sutkikandi",
        "Tatuakandi", "Kodomtuli", "Dariadulat", "Kalainagar"]),
    ("Sonarampur", "সোনারামপুর", "23.7650", "90.7400", [
        "Charmochakandi", "Kanainagar", "Shantipur", "Ishapur", "Dularampur",
        "Ferizzakandi", "Sonarampur", "Charshibpur"]),
    ("Bancharampur", "বাঞ্ছারামপুর", "23.7772", "90.7886", [
        "Dashdona", "Jogonathpur", "Bancharampur", "Dari-Bancharampur",
        "Vitijograrchar", "Durgarampur", "Safirkandi", "Durgapur", "Alipur",
        "Manaikhali", "Ponchampur", "Dhariarchar", "Khoshkandi", "Telikandi",
        "Bhabanathpur"]),
    ("Ayubpur", "আইয়ুবপুর", "23.7550", "90.8000", [
        "Bashgari", "Doshani", "Ayubpur", "Char-chaiani", "Nagarirchar",
        "Kanainagar", "Kashnagar", "Kariyakandi", "Poddapur"]),
    ("Salimabad", "ছলিমাবাদ", "23.7400", "90.7600", [
        "Salimabad", "Shahebnagar", "Nilokhi", "Pakhyarchar", "Satbilla",
        "Kamalpur", "Mirpur", "Asarafbad", "Hossainpur", "Haidornagar",
        "Tatoakandi", "Vurvuria", "Gongachar", "Khagkanda", "Junarchar",
        "Phathamara"]),
    ("Purbo Ujanchar", "পূর্ব উজানচর", "23.7300", "90.8200", [
        "Notonhati", "Sorisharchar", "Shekerkandi", "Ujanchar", "Krishnonagar",
        "Budhaikandi", "Radhanagar", "Kalikapur"]),
    ("Manikpur", "মানিকপুর", "23.7200", "90.7800", [
        "Kayallanpur", "Manikpur", "Charani", "Ulokandi", "Kapaskandi",
        "Do-ani", "Mayarampur", "Baherchar"]),
]


class Command(BaseCommand):
    help = "Seed Bancharampur Upazila unions (as delivery zones) and their villages."

    def add_arguments(self, parser):
        parser.add_argument("--exclusive", action="store_true",
                            help="Deactivate every zone that is not a Bancharampur union.")

    @transaction.atomic
    def handle(self, *args, **opts):
        zones_touched, villages_created = 0, 0
        keep_ids = []
        for name, name_bn, lat, lng, villages in UNIONS:
            zone, _ = DeliveryZone.objects.update_or_create(
                name=name,
                defaults={
                    "name_bn": name_bn,
                    "center_lat": Decimal(lat),
                    "center_lng": Decimal(lng),
                    "radius_km": Decimal("4"),
                    "is_active": True,
                },
            )
            keep_ids.append(zone.id)
            zones_touched += 1
            for v in villages:
                _, made = Village.objects.get_or_create(zone=zone, name=v)
                villages_created += int(made)

        if opts["exclusive"]:
            others = DeliveryZone.objects.exclude(id__in=keep_ids).filter(is_active=True)
            n = others.update(is_active=False)
            self.stdout.write(self.style.WARNING(f"Deactivated {n} non-Bancharampur zone(s)."))

        self.stdout.write(self.style.SUCCESS(
            f"Bancharampur seeded: {zones_touched} unions, {villages_created} new villages."))
