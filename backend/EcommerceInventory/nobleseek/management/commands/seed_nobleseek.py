from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed NobleSeek demo categories + 5 articles (idempotent)."

    def handle(self, *args, **opts):
        from nobleseek.models import Article, NewsCategory
        cats = [("Bangladesh", "bangladesh"), ("World", "world"),
                ("Sports", "sports"), ("Tech", "tech"),
                ("Entertainment", "entertainment")]
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
