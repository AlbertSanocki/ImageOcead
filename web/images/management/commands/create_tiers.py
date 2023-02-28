"""
Django command to create tiers
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from images.models import UserTier

TIERS = [
    {
        "tier_name":"Basic",
        "permissions":{"thumbnail_sizes":[200],"original_image":False,"expiring_links":False}
    },
    {
        "tier_name":"Premium",
        "permissions":{"thumbnail_sizes":[200,400],"original_image":False,"expiring_links":False}
    },
    {
        "tier_name":"Enterprice",
        "permissions":{"thumbnail_sizes":[200,400],"original_image":True,"expiring_links":True}
    },
]


class Command(BaseCommand):
    """Django command to wait for database"""

    help = 'Creates the necessary tiers'

    def handle(self, *args, **options):
        for tier in TIERS:
            new_tier, created = UserTier.objects.get_or_create(name=tier.get("tier_name"))
            new_tier.thumbnail_sizes = tier.get("permissions").get("thumbnail_sizes")
            new_tier.original_image = tier.get("permissions").get("original_image")
            new_tier.expiring_links = tier.get("permissions").get("expiring_links")
            new_tier.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f'Trier {new_tier} created!'))