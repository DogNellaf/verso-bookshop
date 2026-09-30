"""Run periodic jobs (exchange rates, refund retries, stale payments).

python manage.py run_scheduler           # keep running, check every minute
python manage.py run_scheduler --once    # run the due jobs and exit (cron)
python manage.py run_scheduler --once --force   # run every job now
"""

import signal
import time

from django.core.management.base import BaseCommand

from main.scheduler import run_due_jobs


class Command(BaseCommand):
    help = "Run scheduled jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run due jobs once and exit.")
        parser.add_argument("--force", action="store_true", help="Ignore the job intervals.")
        parser.add_argument("--poll", type=int, default=60, help="Seconds between checks.")

    def handle(self, *args, once=False, force=False, poll=60, **options):
        if once:
            self.report(run_due_jobs(force=force))
            return

        self.stopping = False
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.stdout.write(f"Scheduler started, checking every {poll}s.")
        while not self.stopping:
            self.report(run_due_jobs(force=force))
            force = False
            for _ in range(poll):
                if self.stopping:
                    break
                time.sleep(1)
        self.stdout.write("Scheduler stopped.")

    def stop(self, *args):
        self.stopping = True

    def report(self, results):
        for name, ok in results.items():
            style = self.style.SUCCESS if ok else self.style.ERROR
            self.stdout.write(style(f"{name}: {'done' if ok else 'failed'}"))
