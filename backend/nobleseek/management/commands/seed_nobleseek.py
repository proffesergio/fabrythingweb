from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed NobleSeek demo categories + 5 articles (idempotent)."

    def handle(self, *args, **opts):
        from nobleseek.models import Article, NewsCategory
        # Full portal taxonomy (top-news-site sections). Create-only so
        # admin renames/reorders are never clobbered by a redeploy.
        cats = [("বাংলাদেশ", "bangladesh"), ("রাজনীতি", "politics"),
                ("আন্তর্জাতিক", "world"), ("অর্থনীতি", "economy"),
                ("অপরাধ", "crime"), ("আদালত", "court"),
                ("মতামত", "opinion"), ("খেলা", "sports"),
                ("বিনোদন", "entertainment"), ("জীবনযাপন", "lifestyle"),
                ("প্রযুক্তি", "tech"), ("শিক্ষা", "education"),
                ("স্বাস্থ্য", "health"), ("পরিবেশ", "environment"),
                ("প্রবাস", "expatriate"), ("চাকরি", "jobs")]
        cat_map = {}
        for i, (n, s) in enumerate(cats):
            c, _ = NewsCategory.objects.get_or_create(slug=s, defaults={
                "name": n, "display_order": i})
            cat_map[s] = c
        demos = [
            ("bangladesh", "ঢাকায় মেট্রোরেলের নতুন রুট: যা জানা জরুরি | Dhaka Metro New Route",
             "মেট্রোরেলের নতুন অংশের সময়সূচি, ভাড়া ও যাত্রী নির্দেশনা নিয়ে বিস্তারিত।"),
            ("sports", "বাংলাদেশ বনাম ভারত: টানটান উত্তেজনার ম্যাচ | BAN vs IND Thriller",
             "শেষ ওভারের নাটকীয়তা, স্কোরকার্ড ও প্রতিক্রিয়া।"),
            ("tech", "iPhone 17 price in Bangladesh: full breakdown",
             "অফিসিয়াল ও গ্রে-মার্কেট দাম, স্পেসিফিকেশন ও কেনার পরামর্শ।"),
            ("world", "Bitcoin price surges: what it means for BD investors",
             "বিশ্ববাজারের ঊর্ধ্বগতি ও বাংলাদেশি বিনিয়োগকারীদের করণীয়।"),
            ("entertainment", "নতুন ওয়েব সিরিজে ঝড় তুললেন জনপ্রিয় অভিনেতা | Viral Web Series",
             "গল্প, অভিনয় ও দর্শক প্রতিক্রিয়া নিয়ে রিভিউ।"),
        ]
        body = ("<p>NobleSeek ডেমো প্রতিবেদন। এখানে ৬০০-৮০০ শব্দের মূল প্রতিবেদন লিখুন। "
                "Google Trends কীওয়ার্ড থেকে শিরোনাম নিন, নিজস্ব ভাষায় বিস্তারিত লিখুন, "
                "ছবির ক্রেডিট ও তথ্যসূত্র যোগ করুন।</p>" * 12)
        for slug_key, headline, excerpt in demos:
            if Article.objects.filter(headline=headline).exists():
                continue
            Article.objects.create(
                category=cat_map[slug_key], headline=headline, excerpt=excerpt,
                body_html=f"<p><strong>{headline}</strong></p>{body}",
                hero_image="", status=Article.Status.PUBLISHED)
        self.stdout.write(self.style.SUCCESS("NobleSeek demo seeded"))
        self.seed_pages()

    def seed_pages(self):
        """Trust pages editable from the desk (create-only, same idempotency
        contract as categories — admin edits are never overwritten)."""
        from nobleseek.models import FlatPage
        pages = [
            ("about", "আমাদের সম্পর্কে", "সত্যের সন্ধানে, সবার আগে।",
             "<p><strong>নোবেলসিক (NobleSeek)</strong> একটি বাংলা অনলাইন সংবাদমাধ্যম। "
             "দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত আমরা দ্রুত ও নির্ভরযোগ্যভাবে "
             "পাঠকের কাছে পৌঁছে দিই।</p><p>আমাদের প্রতিটি প্রতিবেদন যাচাই করা তথ্যের "
             "ভিত্তিতে তৈরি। ভুল হলে আমরা স্বচ্ছভাবে সংশোধন করি এবং সংশোধনের নোট "
             "প্রতিবেদনে যুক্ত করি। বিজ্ঞাপন ও সম্পাদকীয় বিভাগ সম্পূর্ণ আলাদা — "
             "বিজ্ঞাপনদাতারা সংবাদে হস্তক্ষেপ করতে পারেন না।</p>"),
            ("contact", "যোগাযোগ", "সংবাদ, সংশোধন ও বিজ্ঞাপনের জন্য।",
             "<p><strong>নোবেলসিক নিউজরুম</strong><br/>ঢাকা, বাংলাদেশ<br/>ইমেইল: "
             "<strong>support@fabrything.com</strong><br/>ফোন: +880 1842-168117</p>"
             "<p><strong>সংশোধনের জন্য:</strong> খবরের লিংকসহ সঠিক তথ্য পাঠান — "
             "২৪ ঘণ্টার মধ্যে আপডেট করা হয়।</p><p><strong>বিজ্ঞাপন/পার্টনারশিপ:</strong> "
             "ইমেইলের বিষয়ে “বিজ্ঞাপন” লিখুন।</p>"),
            ("privacy", "গোপনীয়তা নীতি", "আপনার তথ্য কীভাবে ব্যবহার হয়।",
             "<p>পাঠকসংখ্যা পরিমাপ ও বিজ্ঞাপন পরিবেশনের জন্য আমরা Google AdSense, "
             "Google Analytics ও Meta Pixel ব্যবহার করি। এগুলো কুকি সংরক্ষণ করতে পারে। "
             "ব্রাউজার থেকে কুকি বন্ধ করলেও সাইট ব্যবহার করা যায়।</p><p>আমরা কখনো "
             "ব্যক্তিগত তথ্য বিক্রি করি না। মন্তব্য করতে নাম দিতে হয়; ইমেইল নেওয়া হয় না। "
             "তথ্য-সংক্রান্ত অনুরোধে লিখুন: support@fabrything.com।</p>"),
            ("disclaimer", "ডিসক্লেইমার", "পাঠকের জ্ঞাতার্থে।",
             "<p>নোবেলসিকের প্রতিবেদন শুধু তথ্যের উদ্দেশ্যে। আমরা নির্ভরযোগ্য সূত্র থেকে "
             "যাচাই করে প্রকাশ করি; চলমান ঘটনার খবর নতুন তথ্য এলে হালনাগাদ করা হয়। ছবির "
             "সঙ্গে ক্রেডিট দেওয়া থাকে — কোনো ছবির স্বত্বাধিকারী অপসারণ/ক্রেডিট পরিবর্তন "
             "চাইলে যোগাযোগ করুন।</p><p>বিজ্ঞাপন স্পষ্টভাবে চিহ্নিত থাকে এবং তা সম্পাদকীয় "
             "সমর্থন বোঝায় না।</p>"),
            ("ethics", "সম্পাদকীয় নীতি", "যে নীতিতে আমরা সংবাদ প্রকাশ করি।",
             "<ul><li>প্রতিটি প্রকাশের আগে মানব সম্পাদকের যাচাই — খসড়া কখনো সরাসরি প্রকাশ হয় না।</li>"
             "<li>বানোয়াট উদ্ধৃতি নয়, তথ্যহীন চমকপ্রদ শিরোনাম নয়।</li>"
             "<li>ভুল হলে সংশোধন + প্রতিবেদনের নিচে নোট।</li>"
             "<li>ক্রেডিটসহ ছবি; গ্রাফিক/আপত্তিকর কনটেন্ট নয়।</li>"
             "<li>বিজ্ঞাপন ও সম্পাদকীয়র পৃথকীকরণ — বিজ্ঞাপনদাতা কপি অনুমোদন করেন না।</li></ul>"),
        ]
        for slug, title, intro, body in pages:
            FlatPage.objects.get_or_create(
                slug=slug, defaults={"title": title, "intro": intro, "body_html": body})
        self.stdout.write(self.style.SUCCESS("NobleSeek pages seeded"))
