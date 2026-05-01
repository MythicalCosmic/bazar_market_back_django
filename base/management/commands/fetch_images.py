import time
import json
import urllib.request
import urllib.parse
from urllib.error import URLError

from django.core.management.base import BaseCommand
from django.db.models import Q

from base.models import Product, ProductImage, Category


# Common Uzbek grocery terms → English for better search results
UZ_TO_EN = {
    "olma": "apple", "banan": "banana", "uzum": "grape", "nok": "pear",
    "shaftoli": "peach", "anor": "pomegranate", "gilos": "cherry",
    "o'rik": "apricot", "qulupnay": "strawberry", "limon": "lemon",
    "apelsin": "orange", "mandarin": "tangerine", "xurmo": "persimmon",
    "anjir": "fig", "tarvuz": "watermelon", "qovun": "melon",
    "pomidor": "tomato", "bodring": "cucumber", "kartoshka": "potato",
    "piyoz": "onion", "sabzi": "carrot", "karam": "cabbage",
    "qalampir": "pepper", "baqlajon": "eggplant", "rediska": "radish",
    "sarimsoq": "garlic", "lavlagi": "beetroot", "turp": "turnip",
    "kunjut": "sesame", "sut": "milk", "qatiq": "yogurt",
    "tvorog": "cottage cheese", "sariyog'": "butter", "pishloq": "cheese",
    "smetana": "sour cream", "qaymoq": "cream",
    "mol go'shti": "beef", "tovuq": "chicken", "qo'y go'shti": "lamb",
    "baliq": "fish", "kolbasa": "sausage",
    "non": "bread", "oq non": "white bread", "patir": "flatbread",
    "lavash": "lavash bread", "somsa": "samosa pastry",
    "suv": "water bottle", "sharbat": "juice", "choy": "tea",
    "kompot": "compote drink", "qahva": "coffee",
    "guruch": "rice", "makaron": "pasta", "un": "flour",
    "shakar": "sugar", "tuz": "salt", "yog'": "oil",
    "tuxum": "eggs", "asal": "honey",
    # categories
    "mevalar": "fruits", "sabzavotlar": "vegetables",
    "sut mahsulotlari": "dairy products", "go'sht": "meat",
    "non mahsulotlari": "bakery", "ichimliklar": "beverages",
    "oziq-ovqat": "groceries", "ziravorlar": "spices",
}


def _translate(name_uz: str) -> str:
    """Try to translate Uzbek product name to English for better image search."""
    lower = name_uz.lower().strip()
    if lower in UZ_TO_EN:
        return UZ_TO_EN[lower]
    # Try partial matches
    for uz, en in UZ_TO_EN.items():
        if uz in lower or lower in uz:
            return en
    return name_uz


class Command(BaseCommand):
    help = "Fetch product images from Pixabay for products missing images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-key",
            required=True,
            help="Pixabay API key (free at pixabay.com/api/docs/)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max products to process (0 = all)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace existing images (default: skip products that have images)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fetched without saving",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="Delay between API calls in seconds (default: 0.5)",
        )
        parser.add_argument(
            "--category-fallback",
            action="store_true",
            default=True,
            help="If product search fails, search by category name (default: on)",
        )

    def handle(self, *args, **options):
        api_key = options["api_key"]
        limit = options["limit"]
        overwrite = options["overwrite"]
        dry_run = options["dry_run"]
        delay = options["delay"]
        category_fallback = options["category_fallback"]

        # Get products that need images
        products = Product.objects.filter(
            deleted_at__isnull=True, is_active=True
        ).select_related("category")

        if not overwrite:
            # Only products without a primary image
            products = products.exclude(
                images__is_primary=True
            )

        products = products.order_by("id")

        if limit:
            products = products[:limit]

        products = list(products)
        total = len(products)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All products already have images."))
            return

        self.stdout.write(f"Found {total} products needing images")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be saved"))

        success_count = 0
        fail_count = 0
        cache = {}  # cache search results by query to avoid duplicate API calls

        for i, product in enumerate(products, 1):
            query = _translate(product.name_uz)
            category_query = None
            if product.category:
                category_query = _translate(product.category.name_uz)

            # Try product name first
            image_url = self._search_cached(
                api_key, query, cache, f"food {query}"
            )

            # Fallback to category
            if not image_url and category_fallback and category_query:
                image_url = self._search_cached(
                    api_key, category_query, cache, f"food {category_query}"
                )

            if not image_url:
                self.stdout.write(
                    self.style.WARNING(f"  [{i}/{total}] {product.name_uz} — no results")
                )
                fail_count += 1
                continue

            if dry_run:
                self.stdout.write(f"  [{i}/{total}] {product.name_uz} → {image_url[:80]}...")
                success_count += 1
            else:
                if overwrite:
                    ProductImage.objects.filter(
                        product=product, is_primary=True
                    ).delete()

                ProductImage.objects.create(
                    product=product,
                    image=image_url,
                    sort_order=0,
                    is_primary=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  [{i}/{total}] {product.name_uz} ✓")
                )
                success_count += 1

            if delay and query not in cache:
                time.sleep(delay)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done: {success_count} images {'would be ' if dry_run else ''}saved, "
            f"{fail_count} failed, {total} total"
        ))

    def _search_cached(self, api_key, query, cache, search_query):
        if search_query in cache:
            return cache[search_query]

        url = self._fetch_pixabay(api_key, search_query)
        cache[search_query] = url
        return url

    def _fetch_pixabay(self, api_key, query):
        params = urllib.parse.urlencode({
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "category": "food",
            "per_page": 3,
            "safesearch": "true",
            "editors_choice": "false",
            "min_width": 400,
            "min_height": 400,
        })
        url = f"https://pixabay.com/api/?{params}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BazarMarket/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except (URLError, json.JSONDecodeError, TimeoutError) as e:
            self.stderr.write(f"    API error for '{query}': {e}")
            return None

        hits = data.get("hits", [])
        if not hits:
            return None

        # Prefer webformatURL (640px) — good enough for product cards
        return hits[0].get("webformatURL") or hits[0].get("largeImageURL")
