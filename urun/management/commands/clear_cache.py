from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear application cache for performance optimization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key',
            type=str,
            help='Specific cache key to clear',
        )
        parser.add_argument(
            '--pattern',
            type=str,
            help='Clear cache keys matching pattern',
        )

    def handle(self, *args, **options):
        if options['key']:
            cache.delete(options['key'])
            self.stdout.write(
                self.style.SUCCESS(f'Cache key "{options["key"]}" cleared successfully!')
            )
        elif options['pattern']:
            # For local memory cache, we need to clear all
            cache.clear()
            self.stdout.write(
                self.style.SUCCESS(f'All cache cleared (pattern matching not supported in LocMemCache)')
            )
        else:
            cache.clear()
            self.stdout.write(
                self.style.SUCCESS('All cache cleared successfully!')
            )