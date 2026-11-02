from django.core.management.base import BaseCommand
from catalog.models import Categories, Products


# Size charts with measurements in inches
SIZE_CHARTS = {
    "men_top": {
        "S": {"chest": 36, "length": 27, "shoulder": 16},
        "M": {"chest": 38, "length": 28, "shoulder": 17},
        "L": {"chest": 40, "length": 29, "shoulder": 18},
        "XL": {"chest": 42, "length": 30, "shoulder": 19},
        "XXL": {"chest": 44, "length": 31, "shoulder": 20},
    },
    "men_bottom": {
        "S": {"waist": 28, "length": 40, "hip": 36},
        "M": {"waist": 30, "length": 41, "hip": 38},
        "L": {"waist": 32, "length": 42, "hip": 40},
        "XL": {"waist": 34, "length": 43, "hip": 42},
        "XXL": {"waist": 36, "length": 44, "hip": 44},
    },
    "women_top": {
        "S": {"chest": 32, "length": 24, "shoulder": 14},
        "M": {"chest": 34, "length": 25, "shoulder": 15},
        "L": {"chest": 36, "length": 26, "shoulder": 16},
        "XL": {"chest": 38, "length": 27, "shoulder": 17},
        "XXL": {"chest": 40, "length": 28, "shoulder": 18},
    },
    "women_bottom": {
        "S": {"waist": 26, "length": 38, "hip": 34},
        "M": {"waist": 28, "length": 39, "hip": 36},
        "L": {"waist": 30, "length": 40, "hip": 38},
        "XL": {"waist": 32, "length": 41, "hip": 40},
        "XXL": {"waist": 34, "length": 42, "hip": 42},
    },
    "kids": {
        "S": {"chest": 24, "length": 18, "shoulder": 11},
        "M": {"chest": 26, "length": 20, "shoulder": 12},
        "L": {"chest": 28, "length": 22, "shoulder": 13},
        "XL": {"chest": 30, "length": 24, "shoulder": 14},
    },
}

# Real product images using picsum.photos (free, no attribution required for seeding)
# Each category gets a pool of 6 seeds; products cycle through them with 3 images each.
CATEGORY_IMAGE_SEEDS = {
    "men-tshirts":       [338, 1074, 157, 433, 91, 366],
    "men-shirts":        [582, 372, 1005, 239, 593, 110],
    "men-pants":         [274, 395, 674, 513, 218, 785],
    "men-jeans":         [617, 294, 476, 739, 152, 641],
    "men-panjabi":       [534, 809, 312, 167, 780, 349],
    "women-saree":       [324, 712, 439, 893, 251, 668],
    "women-salwar-kameez": [456, 237, 810, 562, 378, 945],
    "women-kurti":       [891, 423, 637, 174, 529, 756],
    "women-tops":        [283, 714, 548, 361, 892, 195],
    "kids-boys":         [180, 447, 619, 803, 256, 374],
    "kids-girls":        [502, 713, 336, 878, 121, 657],
}

# Fallback seeds per gender
GENDER_IMAGE_SEEDS = {
    "MEN":    [338, 1074, 157, 433, 91, 366],
    "WOMEN":  [324, 712, 439, 893, 251, 668],
    "KIDS":   [180, 447, 619, 803, 256, 374],
    "UNISEX": [200, 450, 620, 390, 175, 510],
}

def get_product_images(category_slug, gender, product_index):
    """Return 3 distinct picsum.photos URLs for a product."""
    seeds = CATEGORY_IMAGE_SEEDS.get(category_slug) or GENDER_IMAGE_SEEDS.get(gender, [100, 200, 300, 400, 500, 600])
    offset = (product_index * 3) % len(seeds)
    chosen = [seeds[(offset + i) % len(seeds)] for i in range(3)]
    return [f"https://picsum.photos/seed/{s}/600/800" for s in chosen]

# Category banner/thumbnail images (wider, 4:3 ratio)
CATEGORY_BANNER_IMAGES = {
    "men":    "https://picsum.photos/seed/men_banner/800/600",
    "women":  "https://picsum.photos/seed/women_banner/800/600",
    "kids":   "https://picsum.photos/seed/kids_banner/800/600",
    "unisex": "https://picsum.photos/seed/unisex_banner/800/600",
}

CATEGORIES_DATA = [
    {
        "name": "Men",
        "slug": "men",
        "description": "Men's clothing collection",
        "display_order": 1,
        "children": [
            {"name": "T-Shirts", "slug": "men-tshirts", "description": "Men's t-shirts and casual tops", "display_order": 1},
            {"name": "Shirts", "slug": "men-shirts", "description": "Men's formal and casual shirts", "display_order": 2},
            {"name": "Pants", "slug": "men-pants", "description": "Men's pants and trousers", "display_order": 3},
            {"name": "Jeans", "slug": "men-jeans", "description": "Men's denim jeans", "display_order": 4},
            {"name": "Panjabi", "slug": "men-panjabi", "description": "Men's traditional panjabi", "display_order": 5},
        ],
    },
    {
        "name": "Women",
        "slug": "women",
        "description": "Women's clothing collection",
        "display_order": 2,
        "children": [
            {"name": "Saree", "slug": "women-saree", "description": "Women's sarees", "display_order": 1},
            {"name": "Salwar Kameez", "slug": "women-salwar-kameez", "description": "Women's salwar kameez sets", "display_order": 2},
            {"name": "Kurti", "slug": "women-kurti", "description": "Women's kurtis and tunics", "display_order": 3},
            {"name": "Tops", "slug": "women-tops", "description": "Women's tops and blouses", "display_order": 4},
        ],
    },
    {
        "name": "Kids",
        "slug": "kids",
        "description": "Kids' clothing collection",
        "display_order": 3,
        "children": [
            {"name": "Boys", "slug": "kids-boys", "description": "Boys' clothing", "display_order": 1},
            {"name": "Girls", "slug": "kids-girls", "description": "Girls' clothing", "display_order": 2},
        ],
    },
]

PRODUCTS_DATA = [
    # ── Men's T-Shirts (5) ──
    {"name": "Classic Cotton T-Shirt", "category_slug": "men-tshirts", "gender": "MEN", "material": "100% Cotton",
     "initial_buying_price": 350, "initial_selling_price": 599, "discount_price": 499,
     "color": "Black", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Premium quality cotton t-shirt with a comfortable fit. Perfect for everyday casual wear."},
    {"name": "Polo T-Shirt Premium", "category_slug": "men-tshirts", "gender": "MEN", "material": "Cotton Pique",
     "initial_buying_price": 500, "initial_selling_price": 899, "discount_price": 749,
     "color": "Navy Blue", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Richman",
     "description": "Smart polo t-shirt with collar, ideal for semi-casual occasions."},
    {"name": "Graphic Print T-Shirt", "category_slug": "men-tshirts", "gender": "MEN", "material": "Cotton Jersey",
     "initial_buying_price": 300, "initial_selling_price": 549, "discount_price": 399,
     "color": "White", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Trendy graphic print t-shirt with modern streetwear design. Soft breathable fabric."},
    {"name": "V-Neck Slim Fit T-Shirt", "category_slug": "men-tshirts", "gender": "MEN", "material": "Cotton Spandex",
     "initial_buying_price": 380, "initial_selling_price": 699,
     "color": "Charcoal", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Cats Eye",
     "description": "Slim fit v-neck t-shirt with stretch fabric for maximum comfort and style."},
    {"name": "Henley Full Sleeve T-Shirt", "category_slug": "men-tshirts", "gender": "MEN", "material": "Cotton",
     "initial_buying_price": 450, "initial_selling_price": 799, "discount_price": 649,
     "color": "Olive Green", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Yellow",
     "description": "Classic henley neck full sleeve t-shirt. Perfect for layering in cooler weather."},

    # ── Men's Shirts (4) ──
    {"name": "Formal Cotton Shirt", "category_slug": "men-shirts", "gender": "MEN", "material": "Cotton Blend",
     "initial_buying_price": 600, "initial_selling_price": 1199, "discount_price": 999,
     "color": "White", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Richman",
     "description": "Crisp formal shirt perfect for office and business meetings."},
    {"name": "Slim Fit Casual Shirt", "category_slug": "men-shirts", "gender": "MEN", "material": "Cotton",
     "initial_buying_price": 650, "initial_selling_price": 1299,
     "color": "Light Blue", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Yellow",
     "description": "Modern slim fit casual shirt with button-down collar. Versatile for any occasion."},
    {"name": "Checked Flannel Shirt", "category_slug": "men-shirts", "gender": "MEN", "material": "Cotton Flannel",
     "initial_buying_price": 700, "initial_selling_price": 1399, "discount_price": 1099,
     "color": "Red Check", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Cats Eye",
     "description": "Warm flannel shirt with classic check pattern. Great for casual outings and winter layering."},
    {"name": "Linen Summer Shirt", "category_slug": "men-shirts", "gender": "MEN", "material": "Linen",
     "initial_buying_price": 800, "initial_selling_price": 1599, "discount_price": 1299,
     "color": "Beige", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Breathable linen shirt perfect for hot Bangladeshi summers. Lightweight and stylish."},

    # ── Men's Pants (3) ──
    {"name": "Chino Pants Slim Fit", "category_slug": "men-pants", "gender": "MEN", "material": "Cotton Twill",
     "initial_buying_price": 700, "initial_selling_price": 1399, "discount_price": 1199,
     "color": "Khaki", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Richman",
     "description": "Comfortable slim fit chino pants for a smart casual look."},
    {"name": "Formal Trouser", "category_slug": "men-pants", "gender": "MEN", "material": "Polyester Blend",
     "initial_buying_price": 850, "initial_selling_price": 1699,
     "color": "Charcoal Grey", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_bottom",
     "brand": "Richman",
     "description": "Classic formal trouser with crisp crease. Essential for professional wardrobe."},
    {"name": "Jogger Pants", "category_slug": "men-pants", "gender": "MEN", "material": "Cotton French Terry",
     "initial_buying_price": 550, "initial_selling_price": 999, "discount_price": 799,
     "color": "Black", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Fabrything",
     "description": "Comfortable jogger pants with elastic waist and cuffed hem. Perfect for lounging or workouts."},

    # ── Men's Jeans (3) ──
    {"name": "Slim Fit Denim Jeans", "category_slug": "men-jeans", "gender": "MEN", "material": "Stretch Denim",
     "initial_buying_price": 900, "initial_selling_price": 1799, "discount_price": 1499,
     "color": "Dark Blue", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Cats Eye",
     "description": "Modern slim fit jeans with stretch for comfort. Versatile dark wash for any occasion."},
    {"name": "Straight Fit Classic Jeans", "category_slug": "men-jeans", "gender": "MEN", "material": "100% Denim",
     "initial_buying_price": 850, "initial_selling_price": 1699,
     "color": "Medium Blue", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_bottom",
     "brand": "Yellow",
     "description": "Timeless straight fit jeans. Durable construction with classic 5-pocket styling."},
    {"name": "Ripped Skinny Jeans", "category_slug": "men-jeans", "gender": "MEN", "material": "Stretch Denim",
     "initial_buying_price": 950, "initial_selling_price": 1899, "discount_price": 1399,
     "color": "Faded Black", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Edgy ripped skinny jeans with distressed detailing. Fashion-forward streetwear style."},

    # ── Men's Panjabi (3) ──
    {"name": "Embroidered Cotton Panjabi", "category_slug": "men-panjabi", "gender": "MEN", "material": "Cotton",
     "initial_buying_price": 800, "initial_selling_price": 1599, "discount_price": 1399,
     "color": "Off White", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Aarong",
     "description": "Beautifully embroidered cotton panjabi for festive occasions and Eid celebrations."},
    {"name": "Silk Panjabi Premium", "category_slug": "men-panjabi", "gender": "MEN", "material": "Silk Blend",
     "initial_buying_price": 1500, "initial_selling_price": 3499, "discount_price": 2999,
     "color": "Royal Blue", "available_sizes": ["M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Aarong",
     "description": "Luxurious silk blend panjabi with intricate embroidery. Perfect for weddings and special occasions."},
    {"name": "Printed Lawn Panjabi", "category_slug": "men-panjabi", "gender": "MEN", "material": "Lawn Cotton",
     "initial_buying_price": 700, "initial_selling_price": 1299,
     "color": "Maroon", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Fabrything",
     "description": "Lightweight lawn cotton panjabi with modern prints. Comfortable for daily and semi-formal wear."},

    # ── Women's Saree (4) ──
    {"name": "Jamdani Saree", "category_slug": "women-saree", "gender": "WOMEN", "material": "Cotton Jamdani",
     "initial_buying_price": 2500, "initial_selling_price": 4999, "discount_price": 4499,
     "color": "White & Red", "available_sizes": ["FREE"], "size_chart_key": "women_top",
     "brand": "Aarong",
     "description": "Traditional Bangladeshi Jamdani saree with intricate handwoven patterns. Heritage craftsmanship."},
    {"name": "Silk Banarasi Saree", "category_slug": "women-saree", "gender": "WOMEN", "material": "Pure Silk",
     "initial_buying_price": 4000, "initial_selling_price": 8999, "discount_price": 6999,
     "color": "Gold & Maroon", "available_sizes": ["FREE"], "size_chart_key": "women_top",
     "brand": "Aarong", "addition_details": {"flash_sale": True},
     "description": "Luxurious Banarasi silk saree with rich golden zari work. Perfect for weddings and grand celebrations."},
    {"name": "Printed Georgette Saree", "category_slug": "women-saree", "gender": "WOMEN", "material": "Georgette",
     "initial_buying_price": 1200, "initial_selling_price": 2499,
     "color": "Teal Green", "available_sizes": ["FREE"], "size_chart_key": "women_top",
     "brand": "Fabrything",
     "description": "Elegant printed georgette saree with flowing drape. Lightweight and easy to manage."},
    {"name": "Cotton Tant Saree", "category_slug": "women-saree", "gender": "WOMEN", "material": "Cotton Tant",
     "initial_buying_price": 800, "initial_selling_price": 1999, "discount_price": 1599,
     "color": "Yellow & Black", "available_sizes": ["FREE"], "size_chart_key": "women_top",
     "brand": "Fabrything",
     "description": "Traditional Bengali tant saree in vibrant colors. Comfortable for everyday wear and pujas."},

    # ── Women's Salwar Kameez (4) ──
    {"name": "Printed Salwar Kameez Set", "category_slug": "women-salwar-kameez", "gender": "WOMEN", "material": "Lawn Cotton",
     "initial_buying_price": 1200, "initial_selling_price": 2499, "discount_price": 1999,
     "color": "Blue Floral", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Rang",
     "description": "Elegant printed salwar kameez three-piece set with dupatta. Perfect for casual and semi-formal wear."},
    {"name": "Embroidered Chiffon Salwar Kameez", "category_slug": "women-salwar-kameez", "gender": "WOMEN", "material": "Chiffon",
     "initial_buying_price": 1800, "initial_selling_price": 3499, "discount_price": 2799,
     "color": "Peach", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Aarong", "addition_details": {"flash_sale": True},
     "description": "Stunning embroidered chiffon salwar kameez with intricate threadwork. Ideal for parties and events."},
    {"name": "Cotton Everyday Salwar Set", "category_slug": "women-salwar-kameez", "gender": "WOMEN", "material": "Cotton",
     "initial_buying_price": 800, "initial_selling_price": 1499,
     "color": "Mint Green", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "women_top",
     "brand": "Fabrything",
     "description": "Comfortable cotton salwar kameez for daily wear. Breathable fabric perfect for Bangladesh's climate."},
    {"name": "Designer Anarkali Suit", "category_slug": "women-salwar-kameez", "gender": "WOMEN", "material": "Georgette",
     "initial_buying_price": 2000, "initial_selling_price": 3999, "discount_price": 3299,
     "color": "Wine Red", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Rang",
     "description": "Gorgeous designer anarkali suit with flared silhouette. Makes a statement at any celebration."},

    # ── Women's Kurti (4) ──
    {"name": "Embroidered Kurti", "category_slug": "women-kurti", "gender": "WOMEN", "material": "Cotton",
     "initial_buying_price": 500, "initial_selling_price": 999, "discount_price": 799,
     "color": "Maroon", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Fabrything",
     "description": "Stylish embroidered kurti perfect for casual outings and daily wear."},
    {"name": "A-Line Printed Kurti", "category_slug": "women-kurti", "gender": "WOMEN", "material": "Rayon",
     "initial_buying_price": 400, "initial_selling_price": 799, "discount_price": 599,
     "color": "Indigo Blue", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "women_top",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Trendy A-line kurti with attractive block prints. Comfortable rayon fabric drapes beautifully."},
    {"name": "Straight Cut Formal Kurti", "category_slug": "women-kurti", "gender": "WOMEN", "material": "Cotton Blend",
     "initial_buying_price": 550, "initial_selling_price": 1099,
     "color": "Mustard", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Yellow",
     "description": "Elegant straight cut kurti suitable for office and formal occasions. Clean minimal design."},
    {"name": "Asymmetric Designer Kurti", "category_slug": "women-kurti", "gender": "WOMEN", "material": "Georgette",
     "initial_buying_price": 700, "initial_selling_price": 1399, "discount_price": 999,
     "color": "Coral Pink", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Rang",
     "description": "Fashion-forward asymmetric hem kurti with contemporary design. Stand out with unique style."},

    # ── Women's Tops (4) ──
    {"name": "Casual Crop Top", "category_slug": "women-tops", "gender": "WOMEN", "material": "Cotton Jersey",
     "initial_buying_price": 250, "initial_selling_price": 499, "discount_price": 349,
     "color": "White", "available_sizes": ["S", "M", "L"], "size_chart_key": "women_top",
     "brand": "Fabrything", "addition_details": {"flash_sale": True},
     "description": "Trendy casual crop top for a youthful look. Soft stretchy fabric for all-day comfort."},
    {"name": "Peplum Blouse", "category_slug": "women-tops", "gender": "WOMEN", "material": "Crepe",
     "initial_buying_price": 450, "initial_selling_price": 899,
     "color": "Black", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "women_top",
     "brand": "Yellow",
     "description": "Chic peplum blouse with flattering waist-cinching design. Pairs perfectly with pants or skirts."},
    {"name": "Off-Shoulder Ruffle Top", "category_slug": "women-tops", "gender": "WOMEN", "material": "Cotton Blend",
     "initial_buying_price": 350, "initial_selling_price": 699, "discount_price": 549,
     "color": "Lavender", "available_sizes": ["S", "M", "L"], "size_chart_key": "women_top",
     "brand": "Fabrything",
     "description": "Romantic off-shoulder top with ruffle detailing. Perfect for dates and weekend outings."},
    {"name": "Printed Tunic Top", "category_slug": "women-tops", "gender": "WOMEN", "material": "Rayon",
     "initial_buying_price": 400, "initial_selling_price": 799,
     "color": "Multi Print", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "women_top",
     "brand": "Rang",
     "description": "Flowing tunic top with vibrant prints. Longer length provides modest coverage with style."},

    # ── Kids Boys (5) ──
    {"name": "Boys Cartoon T-Shirt", "category_slug": "kids-boys", "gender": "KIDS", "material": "Cotton",
     "initial_buying_price": 200, "initial_selling_price": 399, "discount_price": 349,
     "color": "Yellow", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Fabrything",
     "description": "Fun cartoon printed t-shirt for boys. Soft and comfortable fabric for active kids."},
    {"name": "Boys Polo Shirt", "category_slug": "kids-boys", "gender": "KIDS", "material": "Cotton Pique",
     "initial_buying_price": 280, "initial_selling_price": 549,
     "color": "Red", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Cats Eye",
     "description": "Smart polo shirt for boys. Great for school and casual outings."},
    {"name": "Boys Denim Shorts", "category_slug": "kids-boys", "gender": "KIDS", "material": "Denim",
     "initial_buying_price": 300, "initial_selling_price": 599, "discount_price": 449,
     "color": "Blue", "available_sizes": ["S", "M", "L"], "size_chart_key": "kids",
     "brand": "Fabrything",
     "description": "Comfortable denim shorts for boys. Perfect for summer play and outdoor activities."},
    {"name": "Boys Tracksuit Set", "category_slug": "kids-boys", "gender": "KIDS", "material": "Polyester",
     "initial_buying_price": 450, "initial_selling_price": 899, "discount_price": 699,
     "color": "Navy & White", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Yellow",
     "description": "Sporty tracksuit set with jacket and pants. Great for sports and everyday active wear."},
    {"name": "Boys Formal Shirt", "category_slug": "kids-boys", "gender": "KIDS", "material": "Cotton",
     "initial_buying_price": 320, "initial_selling_price": 649,
     "color": "Light Blue", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Richman",
     "description": "Smart formal shirt for young gentlemen. Perfect for school events and family occasions."},

    # ── Kids Girls (5) ──
    {"name": "Girls Floral Frock", "category_slug": "kids-girls", "gender": "KIDS", "material": "Cotton Blend",
     "initial_buying_price": 350, "initial_selling_price": 699, "discount_price": 599,
     "color": "Pink", "available_sizes": ["S", "M", "L"], "size_chart_key": "kids",
     "brand": "Fabrything",
     "description": "Adorable floral print frock for girls. Perfect for parties and outings."},
    {"name": "Girls Princess Dress", "category_slug": "kids-girls", "gender": "KIDS", "material": "Satin & Tulle",
     "initial_buying_price": 600, "initial_selling_price": 1199, "discount_price": 899,
     "color": "Lavender", "available_sizes": ["S", "M", "L"], "size_chart_key": "kids",
     "brand": "Fabrything",
     "description": "Enchanting princess dress with tulle skirt. Makes every little girl feel like royalty."},
    {"name": "Girls Cotton Leggings Set", "category_slug": "kids-girls", "gender": "KIDS", "material": "Cotton Spandex",
     "initial_buying_price": 280, "initial_selling_price": 549, "discount_price": 449,
     "color": "Purple", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Cats Eye",
     "description": "Comfortable leggings set with matching top. Perfect for play and everyday wear."},
    {"name": "Girls Denim Dungaree", "category_slug": "kids-girls", "gender": "KIDS", "material": "Denim",
     "initial_buying_price": 400, "initial_selling_price": 799,
     "color": "Blue Denim", "available_sizes": ["S", "M", "L"], "size_chart_key": "kids",
     "brand": "Yellow",
     "description": "Trendy denim dungaree for girls. Fun and fashionable for everyday adventures."},
    {"name": "Girls Embroidered Kurti", "category_slug": "kids-girls", "gender": "KIDS", "material": "Cotton",
     "initial_buying_price": 300, "initial_selling_price": 599, "discount_price": 499,
     "color": "Orange", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "kids",
     "brand": "Aarong",
     "description": "Beautiful embroidered kurti for girls. Traditional design with modern comfort for Eid and festivals."},

    # ── Unisex (6) ──
    {"name": "Unisex Hoodie", "category_slug": "men-tshirts", "gender": "UNISEX", "material": "Cotton Fleece",
     "initial_buying_price": 600, "initial_selling_price": 1199, "discount_price": 899,
     "color": "Grey Melange", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Fabrything",
     "description": "Cozy unisex hoodie with kangaroo pocket. Warm fleece lining perfect for winter evenings."},
    {"name": "Unisex Windbreaker Jacket", "category_slug": "men-shirts", "gender": "UNISEX", "material": "Nylon",
     "initial_buying_price": 800, "initial_selling_price": 1599, "discount_price": 1199,
     "color": "Black", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Fabrything",
     "description": "Lightweight windbreaker jacket with water-resistant coating. Essential for rainy season."},
    {"name": "Unisex Oversized T-Shirt", "category_slug": "men-tshirts", "gender": "UNISEX", "material": "Cotton",
     "initial_buying_price": 350, "initial_selling_price": 649,
     "color": "Cream", "available_sizes": ["S", "M", "L", "XL", "XXL"], "size_chart_key": "men_top",
     "brand": "Fabrything",
     "description": "Relaxed oversized t-shirt in a neutral tone. Minimalist streetwear essential for everyone."},
    {"name": "Unisex Cargo Pants", "category_slug": "men-pants", "gender": "UNISEX", "material": "Cotton Twill",
     "initial_buying_price": 750, "initial_selling_price": 1499, "discount_price": 1099,
     "color": "Olive", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Fabrything",
     "description": "Functional cargo pants with multiple pockets. Durable and stylish for outdoor adventures."},
    {"name": "Unisex Sweatshirt", "category_slug": "men-tshirts", "gender": "UNISEX", "material": "French Terry",
     "initial_buying_price": 550, "initial_selling_price": 999, "discount_price": 749,
     "color": "Dusty Pink", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_top",
     "brand": "Fabrything",
     "description": "Soft french terry sweatshirt in trendy dusty pink. Gender-neutral comfort for all seasons."},
    {"name": "Unisex Linen Pants", "category_slug": "men-pants", "gender": "UNISEX", "material": "Linen",
     "initial_buying_price": 700, "initial_selling_price": 1399,
     "color": "Off White", "available_sizes": ["S", "M", "L", "XL"], "size_chart_key": "men_bottom",
     "brand": "Fabrything",
     "description": "Breezy linen pants for hot days. Relaxed fit with elastic waistband for effortless style."},
]


class Command(BaseCommand):
    help = "Seed the database with sample clothing categories and products"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
        parser.add_argument("--update-images", action="store_true", help="Update images on existing products without recreating them")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing products and categories...")
            Products.objects.all().delete()
            Categories.objects.all().delete()

        self.stdout.write("Creating/updating categories...")
        category_map = {}
        for cat_data in CATEGORIES_DATA:
            cat_image = [CATEGORY_BANNER_IMAGES.get(cat_data["slug"], CATEGORY_BANNER_IMAGES["unisex"])]
            parent, created = Categories.objects.get_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "display_order": cat_data["display_order"],
                    "image": cat_image,
                },
            )
            if not created and options["update_images"]:
                parent.image = cat_image
                parent.save(update_fields=["image"])
            status = "created" if created else "exists"
            self.stdout.write(f"  {parent.name} ({status})")
            category_map[cat_data["slug"]] = parent

            for child_data in cat_data.get("children", []):
                child_image = [CATEGORY_BANNER_IMAGES.get(cat_data["slug"], CATEGORY_BANNER_IMAGES["unisex"])]
                child, created = Categories.objects.get_or_create(
                    slug=child_data["slug"],
                    defaults={
                        "name": child_data["name"],
                        "description": child_data["description"],
                        "display_order": child_data["display_order"],
                        "parent_id": parent,
                        "image": child_image,
                    },
                )
                if not created and options["update_images"]:
                    child.image = child_image
                    child.save(update_fields=["image"])
                status = "created" if created else "exists"
                self.stdout.write(f"    {child.name} ({status})")
                category_map[child_data["slug"]] = child

        self.stdout.write("\nCreating/updating products...")
        sku_counter = 1000
        # Track per-category product index so each product in a category gets distinct images
        category_product_index = {}

        for prod_data in PRODUCTS_DATA:
            sku_counter += 1
            sku = f"FAB-{sku_counter}"
            category_slug = prod_data["category_slug"]
            category = category_map.get(category_slug)

            cat_idx = category_product_index.get(category_slug, 0)
            category_product_index[category_slug] = cat_idx + 1
            images = get_product_images(category_slug, prod_data["gender"], cat_idx)

            product, created = Products.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": prod_data["name"],
                    "slug": prod_data["name"].lower().replace(" ", "-").replace("'", ""),
                    "description": prod_data["description"],
                    "image": images,
                    "initial_buying_price": prod_data["initial_buying_price"],
                    "initial_selling_price": prod_data["initial_selling_price"],
                    "discount_price": prod_data.get("discount_price"),
                    "gender": prod_data["gender"],
                    "material": prod_data["material"],
                    "color": prod_data["color"],
                    "brand": prod_data.get("brand", "Fabrything"),
                    "available_sizes": prod_data["available_sizes"],
                    "size_chart": SIZE_CHARTS.get(prod_data["size_chart_key"], {}),
                    "category_id": category,
                    "status": "ACTIVE",
                    "addition_details": prod_data.get("addition_details", {}),
                    "specifications": {
                        "material": prod_data["material"],
                        "color": prod_data["color"],
                        "brand": prod_data.get("brand", "Fabrything"),
                        "gender": prod_data["gender"],
                    },
                    "highlights": [
                        f"Material: {prod_data['material']}",
                        f"Color: {prod_data['color']}",
                        f"Available sizes: {', '.join(prod_data['available_sizes'])}",
                        f"Brand: {prod_data.get('brand', 'Fabrything')}",
                    ],
                    "seo_title": prod_data["name"] + " - Fabrything",
                    "seo_description": prod_data["description"][:160],
                    "seo_keywords": [prod_data["gender"].lower(), prod_data["material"].lower(), "fabrything"],
                },
            )

            if not created and options["update_images"]:
                product.image = images
                product.status = "ACTIVE"
                product.save(update_fields=["image", "status"])

            action = "created" if created else ("images updated" if options["update_images"] else "exists")
            self.stdout.write(f"  {product.name} [{sku}] ({action})")

        total_categories = Categories.objects.count()
        total_products = Products.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete! {total_categories} categories, {total_products} products in DB."
            )
        )
