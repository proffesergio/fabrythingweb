from django.core.management.base import BaseCommand

from catalog.services_sync_jobs import run_once


class Command(BaseCommand):
    help = 'Process scheduled catalog and Google integration jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--poll-seconds', type=int, default=15)

    def handle(self, *args, **options):
        import time
        if not 5 <= options['poll_seconds'] <= 300:
            raise ValueError('--poll-seconds must be between 5 and 300')
        while True:
            run = run_once()
            if run:
                self.stdout.write(f'Sync run {run.pk}: {run.status}')
            if not options['loop']:
                break
            time.sleep(options['poll_seconds'])
