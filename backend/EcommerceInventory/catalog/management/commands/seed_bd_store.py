"""
Seed a realistic Bangladeshi multi-category storefront.

Curated, real-brand catalog spanning Men's & Women's fashion, shoes, watches,
eyewear, wallets & bags, home appliances, and skincare & cosmetics — with
realistic BDT pricing. Product imagery uses themed loremflickr placeholders
(stable per `lock`); replace with real product photography via the admin later.

    python manage.py seed_bd_store            # clears catalog, then seeds
    python manage.py seed_bd_store --keep     # seed without clearing

Idempotent on categories/products by slug. `seed_demo` calls this, then builds
sellable variants + stock and the store configuration.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Categories, Products


def img(keyword, lock):
    """A themed, stable placeholder image URL (Creative Commons via loremflickr)."""
    return f"https://loremflickr.com/600/800/{keyword}?lock={lock}"


def images_for(keyword, base_lock, n=3):
    return [img(keyword, base_lock + i) for i in range(n)]


# ── Categories (top level) ────────────────────────────────────────────────────
CATEGORIES = [
    {"slug": "mens-fashion", "name": "Men's Fashion", "order": 1, "kw": "man,fashion",
     "desc": "Panjabi, shirts, pants, jackets & suits from Bangladesh's top labels."},
    {"slug": "womens-fashion", "name": "Women's Fashion", "order": 2, "kw": "woman,fashion",
     "desc": "Sarees, kameez, kurti, dresses & tops — heritage to contemporary."},
    {"slug": "shoes", "name": "Shoes", "order": 3, "kw": "shoes",
     "desc": "Formal, casual & sport footwear from Apex, Bata, Bay & more."},
    {"slug": "watches", "name": "Watches", "order": 4, "kw": "wristwatch",
     "desc": "Analog & smart watches from Fastrack, Titan, Casio & Fossil."},
    {"slug": "eyewear", "name": "Eyewear", "order": 5, "kw": "sunglasses",
     "desc": "Sunglasses & optical frames — Ray-Ban, Oakley, Titan Eye+."},
    {"slug": "wallets-bags", "name": "Wallets & Bags", "order": 6, "kw": "wallet,leather",
     "desc": "Genuine leather wallets, belts, handbags & laptop bags."},
    {"slug": "home-appliances", "name": "Home Appliances", "order": 7, "kw": "appliance",
     "desc": "Fridges, ACs, TVs & kitchen appliances from Walton, Vision & Singer."},
    {"slug": "skincare-cosmetics", "name": "Skincare & Cosmetics", "order": 8, "kw": "cosmetics",
     "desc": "Serums, cleansers & makeup — Skin Cafe, Pond's, Lakmé, The Body Shop."},
]

CLOTHING_SIZES = ["S", "M", "L", "XL"]
SHOE_SIZES = ["39", "40", "41", "42", "43"]

# ── Products ──────────────────────────────────────────────────────────────────
# sell = selling price (BDT); disc = discounted price (optional); buy defaults to ~68% of sell.
P = [
    # ---- Men's Fashion ----
    {"cat": "mens-fashion", "name": "Aarong Handloom Cotton Panjabi", "brand": "Aarong", "gender": "MEN",
     "sell": 2490, "disc": 1990, "color": "Off White", "material": "Handloom Cotton", "sizes": CLOTHING_SIZES,
     "img": "panjabi,man", "desc": "Handcrafted handloom cotton panjabi with subtle karchupi work — Aarong's signature Eid essential."},
    {"cat": "mens-fashion", "name": "Cats Eye Slim Fit Formal Shirt", "brand": "Cats Eye", "gender": "MEN",
     "sell": 1890, "color": "Sky Blue", "material": "Cotton Twill", "sizes": CLOTHING_SIZES,
     "img": "man,shirt", "desc": "Wrinkle-resistant slim-fit formal shirt, tailored for the Dhaka boardroom."},
    {"cat": "mens-fashion", "name": "Yellow Premium Chino Pants", "brand": "Yellow", "gender": "MEN",
     "sell": 2190, "disc": 1750, "color": "Khaki", "material": "Stretch Cotton", "sizes": CLOTHING_SIZES,
     "img": "chino,pants", "desc": "Smart-casual stretch chinos with a clean tapered leg — office to weekend."},
    {"cat": "mens-fashion", "name": "Ecstasy Graphic Crew Tee", "brand": "Ecstasy", "gender": "MEN",
     "sell": 890, "color": "Charcoal", "material": "Combed Cotton", "sizes": CLOTHING_SIZES,
     "img": "man,tshirt", "desc": "Soft combed-cotton tee with a bold front graphic — everyday youth staple."},
    {"cat": "mens-fashion", "name": "Le Reve Washed Denim Jacket", "brand": "Le Reve", "gender": "MEN",
     "sell": 3490, "disc": 2790, "color": "Mid Blue", "material": "Denim", "sizes": CLOTHING_SIZES,
     "img": "denim,jacket", "desc": "Vintage-washed denim trucker jacket with a modern boxy cut."},
    {"cat": "mens-fashion", "name": "Richman Two-Piece Formal Suit", "brand": "Richman", "gender": "MEN",
     "sell": 8990, "color": "Navy", "material": "Poly-Viscose", "sizes": CLOTHING_SIZES,
     "img": "suit,man", "desc": "Structured two-piece suit with a tailored notch lapel for weddings & work."},
    {"cat": "mens-fashion", "name": "Sailor Pique Polo Shirt", "brand": "Sailor", "gender": "MEN",
     "sell": 1190, "color": "Forest Green", "material": "Pique Cotton", "sizes": CLOTHING_SIZES,
     "img": "polo,shirt", "desc": "Breathable pique polo with ribbed collar — smart casual done right."},
    {"cat": "mens-fashion", "name": "Artisan Embroidered Panjabi", "brand": "Artisan", "gender": "MEN",
     "sell": 3290, "disc": 2690, "color": "Maroon", "material": "Cotton Blend", "sizes": CLOTHING_SIZES,
     "img": "panjabi", "desc": "Festive panjabi with fine chest embroidery for Eid and celebrations."},

    # ---- Women's Fashion ----
    {"cat": "womens-fashion", "name": "Aarong Half-Silk Jamdani Saree", "brand": "Aarong", "gender": "WOMEN",
     "sell": 6500, "disc": 5200, "color": "Deep Red", "material": "Half Silk", "sizes": ["FREE"],
     "img": "saree", "desc": "Handwoven jamdani-motif half-silk saree — timeless heritage craftsmanship."},
    {"cat": "womens-fashion", "name": "Kay Kraft Embroidered Kameez", "brand": "Kay Kraft", "gender": "WOMEN",
     "sell": 2890, "color": "Teal", "material": "Viscose", "sizes": CLOTHING_SIZES,
     "img": "kameez,dress", "desc": "Flowy embroidered kameez with contrast piping for festive daywear."},
    {"cat": "womens-fashion", "name": "Yellow Printed Kurti", "brand": "Yellow", "gender": "WOMEN",
     "sell": 1490, "disc": 1190, "color": "Mustard", "material": "Rayon", "sizes": CLOTHING_SIZES,
     "img": "kurti,woman", "desc": "Lightweight printed kurti with a relaxed A-line silhouette."},
    {"cat": "womens-fashion", "name": "Sara Lifestyle Three-Piece Set", "brand": "Sara Lifestyle", "gender": "WOMEN",
     "sell": 3990, "disc": 3290, "color": "Lavender", "material": "Georgette", "sizes": CLOTHING_SIZES,
     "img": "woman,dress", "desc": "Coordinated georgette three-piece with dupatta — ready for any occasion."},
    {"cat": "womens-fashion", "name": "Ecstasy Western Crop Top", "brand": "Ecstasy", "gender": "WOMEN",
     "sell": 990, "color": "Black", "material": "Cotton Lycra", "sizes": CLOTHING_SIZES,
     "img": "woman,top", "desc": "Fitted western crop top that layers effortlessly for a trendy look."},
    {"cat": "womens-fashion", "name": "Le Reve Floral Maxi Dress", "brand": "Le Reve", "gender": "WOMEN",
     "sell": 2790, "disc": 2190, "color": "Blush Pink", "material": "Crepe", "sizes": CLOTHING_SIZES,
     "img": "maxi,dress", "desc": "Floaty floral maxi with a cinched waist — brunch to evening."},
    {"cat": "womens-fashion", "name": "Rang Bangladesh Cotton Saree", "brand": "Rang Bangladesh", "gender": "WOMEN",
     "sell": 2200, "color": "Indigo", "material": "Cotton", "sizes": ["FREE"],
     "img": "saree,cotton", "desc": "Breathable block-print cotton saree celebrating Bengali motifs."},
    {"cat": "womens-fashion", "name": "Nabila Sequin Party Gown", "brand": "Nabila", "gender": "WOMEN",
     "sell": 5990, "disc": 4990, "color": "Emerald", "material": "Satin", "sizes": CLOTHING_SIZES,
     "img": "gown,party", "desc": "Floor-length satin gown with sequin detailing for a statement entrance."},

    # ---- Shoes ----
    {"cat": "shoes", "name": "Apex Men's Formal Leather Shoes", "brand": "Apex", "gender": "MEN",
     "sell": 3990, "disc": 3190, "color": "Black", "material": "Genuine Leather", "sizes": SHOE_SIZES,
     "img": "leather,shoes", "desc": "Hand-finished genuine leather derby — polished comfort for long days."},
    {"cat": "shoes", "name": "Bata Comfit Slip-On Loafers", "brand": "Bata", "gender": "MEN",
     "sell": 2490, "color": "Tan", "material": "Synthetic Leather", "sizes": SHOE_SIZES,
     "img": "loafers,shoes", "desc": "Cushioned Comfit loafers with flexible soles for all-day wear."},
    {"cat": "shoes", "name": "Bay Street Sneakers", "brand": "Bay", "gender": "UNISEX",
     "sell": 2990, "disc": 2490, "color": "White", "material": "Mesh & PU", "sizes": SHOE_SIZES,
     "img": "sneakers", "desc": "Clean everyday sneakers with breathable mesh and a chunky sole."},
    {"cat": "shoes", "name": "Apex Women's Block Heels", "brand": "Apex", "gender": "WOMEN",
     "sell": 2790, "color": "Nude", "material": "Suede Finish", "sizes": ["36", "37", "38", "39"],
     "img": "heels,shoes", "desc": "Comfortable block heels that dress up any outfit without the ache."},
    {"cat": "shoes", "name": "Lotto Vector Running Shoes", "brand": "Lotto", "gender": "UNISEX",
     "sell": 3490, "disc": 2790, "color": "Grey/Lime", "material": "Knit Mesh", "sizes": SHOE_SIZES,
     "img": "running,shoes", "desc": "Lightweight running shoes with responsive cushioning for daily miles."},
    {"cat": "shoes", "name": "Jennys Strappy Sandals", "brand": "Jennys", "gender": "WOMEN",
     "sell": 1490, "color": "Rose Gold", "material": "PU", "sizes": ["36", "37", "38", "39"],
     "img": "sandals,women", "desc": "Delicate strappy sandals with a low heel for effortless summer style."},
    {"cat": "shoes", "name": "Leatherland Chelsea Boots", "brand": "Leatherland", "gender": "MEN",
     "sell": 5490, "disc": 4690, "color": "Brown", "material": "Full-Grain Leather", "sizes": SHOE_SIZES,
     "img": "chelsea,boots", "desc": "Full-grain leather Chelsea boots with elastic gussets and a Goodyear look."},

    # ---- Watches ----
    {"cat": "watches", "name": "Fastrack Analog Blue Dial", "brand": "Fastrack", "gender": "UNISEX",
     "sell": 4990, "disc": 3990, "color": "Blue", "material": "Stainless Steel", "sizes": [],
     "img": "wristwatch,blue", "desc": "Minimal analog watch with a sunray blue dial and steel mesh strap."},
    {"cat": "watches", "name": "Titan Neo Leather Watch", "brand": "Titan", "gender": "MEN",
     "sell": 8990, "color": "Brown", "material": "Leather Strap", "sizes": [],
     "img": "wristwatch,leather", "desc": "Classic Titan Neo with a champagne dial and genuine leather strap."},
    {"cat": "watches", "name": "Casio Enticer Chronograph", "brand": "Casio", "gender": "MEN",
     "sell": 6490, "color": "Silver", "material": "Stainless Steel", "sizes": [],
     "img": "chronograph,watch", "desc": "Casio Enticer chronograph with day-date and a scratch-resistant crystal."},
    {"cat": "watches", "name": "Casio G-Shock GA-2100", "brand": "Casio", "gender": "UNISEX",
     "sell": 12990, "disc": 10990, "color": "Black", "material": "Resin", "sizes": [],
     "img": "gshock,watch", "desc": "Shock-resistant, 200m water-resistant G-Shock with the iconic octagon bezel."},
    {"cat": "watches", "name": "Fossil Gen Minimalist", "brand": "Fossil", "gender": "MEN",
     "sell": 15990, "disc": 13490, "color": "Rose Gold", "material": "Leather Strap", "sizes": [],
     "img": "fossil,watch", "desc": "Slim minimalist Fossil dress watch with a warm rose-gold case."},
    {"cat": "watches", "name": "Fastrack Ruffles Women's Watch", "brand": "Fastrack", "gender": "WOMEN",
     "sell": 3990, "color": "Rose", "material": "Stainless Steel", "sizes": [],
     "img": "watch,women", "desc": "Petite everyday watch with a rose-tone bracelet and mother-of-pearl dial."},

    # ---- Eyewear ----
    {"cat": "eyewear", "name": "Ray-Ban Aviator Classic", "brand": "Ray-Ban", "gender": "UNISEX",
     "sell": 12990, "disc": 10490, "color": "Gold/Green", "material": "Metal", "sizes": [],
     "img": "aviator,sunglasses", "desc": "The original Aviator with G-15 lenses and a gold teardrop frame."},
    {"cat": "eyewear", "name": "Ray-Ban Wayfarer", "brand": "Ray-Ban", "gender": "UNISEX",
     "sell": 11990, "color": "Black", "material": "Acetate", "sizes": [],
     "img": "wayfarer,sunglasses", "desc": "Timeless Wayfarer silhouette in glossy black acetate."},
    {"cat": "eyewear", "name": "Oakley Holbrook", "brand": "Oakley", "gender": "MEN",
     "sell": 14990, "disc": 12990, "color": "Matte Black", "material": "O-Matter", "sizes": [],
     "img": "oakley,sunglasses", "desc": "Sporty Holbrook with Prizm lenses and lightweight O-Matter frame."},
    {"cat": "eyewear", "name": "Fastrack Wraparound Sunglasses", "brand": "Fastrack", "gender": "UNISEX",
     "sell": 1990, "disc": 1490, "color": "Black/Red", "material": "Polycarbonate", "sizes": [],
     "img": "sports,sunglasses", "desc": "Budget-friendly wraparound shades with full UV400 protection."},
    {"cat": "eyewear", "name": "Titan Eye+ Optical Frame", "brand": "Titan Eye+", "gender": "UNISEX",
     "sell": 2990, "color": "Gunmetal", "material": "Metal Alloy", "sizes": [],
     "img": "eyeglasses,frame", "desc": "Lightweight prescription-ready optical frame with spring hinges."},
    {"cat": "eyewear", "name": "Vincent Chase Blue-Light Glasses", "brand": "Vincent Chase", "gender": "UNISEX",
     "sell": 1490, "color": "Transparent", "material": "TR90", "sizes": [],
     "img": "eyeglasses,blue", "desc": "Blue-light-filtering computer glasses for screen-heavy days."},

    # ---- Wallets & Bags ----
    {"cat": "wallets-bags", "name": "Leatherland Bifold Wallet", "brand": "Leatherland", "gender": "MEN",
     "sell": 1890, "disc": 1490, "color": "Dark Brown", "material": "Genuine Leather", "sizes": [],
     "img": "wallet,leather", "desc": "Slim bifold in full-grain leather with RFID-blocking card slots."},
    {"cat": "wallets-bags", "name": "Aarong Leather Long Wallet", "brand": "Aarong", "gender": "UNISEX",
     "sell": 1690, "color": "Tan", "material": "Vegetable-Tanned Leather", "sizes": [],
     "img": "wallet,brown", "desc": "Hand-stitched long wallet crafted by Aarong's leather artisans."},
    {"cat": "wallets-bags", "name": "Brava Structured Handbag", "brand": "Brava", "gender": "WOMEN",
     "sell": 3490, "disc": 2790, "color": "Beige", "material": "Vegan Leather", "sizes": [],
     "img": "handbag,women", "desc": "Structured top-handle handbag with gold hardware and a detachable strap."},
    {"cat": "wallets-bags", "name": "Jared Travel Money Bag", "brand": "Jared", "gender": "UNISEX",
     "sell": 2490, "color": "Black", "material": "Leather", "sizes": [],
     "img": "leather,bag", "desc": "Compact zip-around travel organizer for cash, cards and passport."},
    {"cat": "wallets-bags", "name": "Leatherland Laptop Messenger Bag", "brand": "Leatherland", "gender": "UNISEX",
     "sell": 4990, "disc": 4190, "color": "Coffee", "material": "Genuine Leather", "sizes": [],
     "img": "messenger,bag", "desc": "Padded 15\" laptop messenger in rich coffee leather for the daily commute."},
    {"cat": "wallets-bags", "name": "Apex Reversible Leather Belt", "brand": "Apex", "gender": "MEN",
     "sell": 1290, "color": "Black/Brown", "material": "Genuine Leather", "sizes": [],
     "img": "leather,belt", "desc": "Two-in-one reversible leather belt with a rotating buckle."},

    # ---- Home Appliances ----
    {"cat": "home-appliances", "name": "Walton Frost-Free Refrigerator 386L", "brand": "Walton", "gender": "UNISEX",
     "sell": 62900, "disc": 58900, "color": "Silver", "material": "Steel", "sizes": [],
     "img": "refrigerator", "desc": "Energy-efficient 386L frost-free fridge with inverter compressor and 12-year warranty."},
    {"cat": "home-appliances", "name": "Vision 43\" Full HD Smart LED TV", "brand": "Vision", "gender": "UNISEX",
     "sell": 38990, "disc": 34990, "color": "Black", "material": "Plastic/Glass", "sizes": [],
     "img": "television", "desc": "43-inch Full HD smart LED TV with built-in apps and voice remote."},
    {"cat": "home-appliances", "name": "Walton 1.5 Ton Inverter AC", "brand": "Walton", "gender": "UNISEX",
     "sell": 54900, "disc": 49900, "color": "White", "material": "Steel", "sizes": [],
     "img": "air,conditioner", "desc": "1.5-ton inverter split AC with rapid cooling and anti-viral filter."},
    {"cat": "home-appliances", "name": "Singer Front-Load Washing Machine", "brand": "Singer", "gender": "UNISEX",
     "sell": 32990, "color": "White", "material": "Steel", "sizes": [],
     "img": "washing,machine", "desc": "7kg front-load washer with 15 programs and a quiet inverter motor."},
    {"cat": "home-appliances", "name": "Vision Microwave Oven 25L", "brand": "Vision", "gender": "UNISEX",
     "sell": 11990, "disc": 10490, "color": "Black", "material": "Steel", "sizes": [],
     "img": "microwave", "desc": "25L convection microwave with grill and auto-cook menus."},
    {"cat": "home-appliances", "name": "Miyako Deluxe Rice Cooker 2.8L", "brand": "Miyako", "gender": "UNISEX",
     "sell": 3490, "color": "White", "material": "Aluminium", "sizes": [],
     "img": "rice,cooker", "desc": "2.8L rice cooker with keep-warm and a durable non-stick inner pot."},
    {"cat": "home-appliances", "name": "Walton Power Blender 1.5L", "brand": "Walton", "gender": "UNISEX",
     "sell": 2790, "disc": 2290, "color": "Grey", "material": "Plastic/Glass", "sizes": [],
     "img": "blender", "desc": "400W blender with stainless blades and an unbreakable jar for daily smoothies."},
    {"cat": "home-appliances", "name": "Minister Energy-Saving Ceiling Fan", "brand": "Minister", "gender": "UNISEX",
     "sell": 3290, "color": "Off White", "material": "Metal", "sizes": [],
     "img": "ceiling,fan", "desc": "56-inch high-speed ceiling fan with a copper motor and 100% pure copper winding."},

    # ---- Skincare & Cosmetics ----
    {"cat": "skincare-cosmetics", "name": "Skin Cafe Vitamin C Serum", "brand": "Skin Cafe", "gender": "UNISEX",
     "sell": 850, "disc": 690, "color": "—", "material": "10% Vitamin C", "sizes": [],
     "img": "serum,skincare", "desc": "Brightening 10% vitamin C serum from Bangladesh's own Skin Cafe."},
    {"cat": "skincare-cosmetics", "name": "Skin Cafe Hyaluronic Acid Serum", "brand": "Skin Cafe", "gender": "UNISEX",
     "sell": 780, "color": "—", "material": "Hyaluronic Acid", "sizes": [],
     "img": "serum,cosmetics", "desc": "Deep-hydration hyaluronic serum that plumps and smooths dry skin."},
    {"cat": "skincare-cosmetics", "name": "Pond's Age Miracle Day Cream", "brand": "Pond's", "gender": "WOMEN",
     "sell": 1150, "color": "—", "material": "Retinol-C Complex", "sizes": [],
     "img": "face,cream", "desc": "Anti-ageing day cream with SPF that visibly firms and brightens."},
    {"cat": "skincare-cosmetics", "name": "Himalaya Neem Face Wash", "brand": "Himalaya", "gender": "UNISEX",
     "sell": 320, "color": "—", "material": "Neem & Turmeric", "sizes": [],
     "img": "facewash", "desc": "Purifying neem face wash that fights acne and controls oil."},
    {"cat": "skincare-cosmetics", "name": "Simple Kind to Skin Cleanser", "brand": "Simple", "gender": "UNISEX",
     "sell": 890, "disc": 750, "color": "—", "material": "Micellar", "sizes": [],
     "img": "cleanser,skincare", "desc": "Fragrance-free micellar cleanser for sensitive skin — no harsh residue."},
    {"cat": "skincare-cosmetics", "name": "Lakmé 9to5 Primer + Matte Foundation", "brand": "Lakmé", "gender": "WOMEN",
     "sell": 1290, "disc": 990, "color": "Warm Beige", "material": "Liquid Foundation", "sizes": [],
     "img": "foundation,makeup", "desc": "Long-wear matte foundation with built-in primer for a 16-hour finish."},
    {"cat": "skincare-cosmetics", "name": "Maybelline Fit Me Compact Powder", "brand": "Maybelline", "gender": "WOMEN",
     "sell": 750, "color": "Natural Beige", "material": "Pressed Powder", "sizes": [],
     "img": "compact,makeup", "desc": "Poreless pressed powder that mattifies without caking."},
    {"cat": "skincare-cosmetics", "name": "The Body Shop Tea Tree Oil", "brand": "The Body Shop", "gender": "UNISEX",
     "sell": 1590, "color": "—", "material": "Tea Tree Oil", "sizes": [],
     "img": "essential,oil", "desc": "Community-trade tea tree oil to target blemishes and clarify skin."},
    {"cat": "skincare-cosmetics", "name": "Nature Republic Aloe Vera 92% Gel", "brand": "Nature Republic", "gender": "UNISEX",
     "sell": 690, "disc": 550, "color": "—", "material": "92% Aloe Vera", "sizes": [],
     "img": "aloe,gel", "desc": "Multi-use soothing aloe gel for face, body and after-sun care."},
    {"cat": "skincare-cosmetics", "name": "L'Oréal Paris Color Riche Lipstick", "brand": "L'Oréal Paris", "gender": "WOMEN",
     "sell": 1190, "color": "Blake Red", "material": "Satin Lipstick", "sizes": [],
     "img": "lipstick,makeup", "desc": "Creamy satin lipstick with intense colour payoff and nourishing oils."},
]


class Command(BaseCommand):
    help = "Seed a realistic Bangladeshi multi-category, real-brand storefront."

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true",
                            help="Do not clear existing catalog before seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["keep"]:
            self.stdout.write("Clearing existing products and categories...")
            Products.objects.all().delete()
            Categories.objects.all().delete()

        # Categories
        lock = 1000
        cat_map = {}
        self.stdout.write("Creating categories...")
        for c in CATEGORIES:
            lock += 1
            cat, _ = Categories.objects.get_or_create(
                slug=c["slug"],
                defaults={
                    "name": c["name"], "description": c["desc"],
                    "display_order": c["order"], "image": [img(c["kw"], lock)],
                },
            )
            cat_map[c["slug"]] = cat
            self.stdout.write(f"  {cat.name}")

        # Products
        self.stdout.write("Creating products...")
        sku_n = 5000
        created = 0
        for p in P:
            sku_n += 1
            lock += 3
            keyword = p.get("img", CATEGORIES_BY_SLUG(p["cat"]))
            gallery = images_for(keyword, lock)
            sell = float(p["sell"])
            disc = float(p["disc"]) if p.get("disc") else None
            buy = round(sell * 0.68)

            product, was_created = Products.objects.get_or_create(
                sku=f"FT-{sku_n}",
                defaults={
                    "name": p["name"],
                    "slug": slugify(p["name"]),
                    "description": p["desc"],
                    "image": gallery,
                    "initial_buying_price": buy,
                    "initial_selling_price": sell,
                    "discount_price": disc,
                    "gender": p["gender"],
                    "material": p["material"],
                    "color": p["color"],
                    "brand": p["brand"],
                    "available_sizes": p["sizes"],
                    "category_id": cat_map[p["cat"]],
                    "status": "ACTIVE",
                    "weight": 0.4,
                    "specifications": {
                        "Brand": p["brand"], "Material": p["material"],
                        "Color": p["color"], "Category": cat_map[p["cat"]].name,
                    },
                    "highlights": [
                        f"Brand: {p['brand']}",
                        f"Material: {p['material']}",
                        f"Color: {p['color']}",
                        "Authentic — 100% genuine product",
                        "Cash on Delivery available",
                    ],
                    "seo_title": f"{p['name']} - Fabrything",
                    "seo_description": p["desc"][:160],
                    "seo_keywords": [p["brand"].lower(), cat_map[p["cat"]].name.lower(), p["gender"].lower()],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. {Categories.objects.count()} categories, {created} new products "
            f"({Products.objects.count()} total)."
        ))


def CATEGORIES_BY_SLUG(slug):
    for c in CATEGORIES:
        if c["slug"] == slug:
            return c["kw"]
    return "product"
