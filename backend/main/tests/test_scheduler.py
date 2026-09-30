from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from main import scheduler
from main.models import JobRun, Order, Payment
from main.tests.helpers import make_user

JOB_NAMES = {"update_exchange_rates", "retry_refunds", "expire_stale_payments"}


def quiet_rates():
    return mock.patch.object(scheduler, "update_exchange_rates", return_value="rates ok")


class SchedulerTest(TestCase):
    def run_jobs(self, now=None, force=False):
        with quiet_rates():
            return scheduler.run_due_jobs(now=now, force=force)

    def test_jobs_run_once_per_interval(self):
        now = timezone.now()
        self.assertEqual(set(self.run_jobs(now)), JOB_NAMES)
        self.assertEqual(self.run_jobs(now + timedelta(minutes=5)), {})

        later = self.run_jobs(now + timedelta(minutes=16))
        self.assertEqual(set(later), {"retry_refunds"})
        self.assertEqual(set(self.run_jobs(now + timedelta(hours=25))), JOB_NAMES)

    def test_runs_are_recorded(self):
        self.run_jobs()
        run = JobRun.objects.get(name="update_exchange_rates")
        self.assertTrue(run.succeeded)
        self.assertEqual(run.message, "rates ok")
        self.assertIsNotNone(run.last_finished)

    def test_a_failing_job_does_not_stop_the_others(self):
        with mock.patch.object(scheduler, "retry_refunds", side_effect=RuntimeError("boom")):
            results = self.run_jobs()
        self.assertFalse(results["retry_refunds"])
        self.assertTrue(results["expire_stale_payments"])
        self.assertEqual(JobRun.objects.get(name="retry_refunds").message, "RuntimeError: boom")

    def test_force_ignores_intervals(self):
        self.run_jobs()
        self.assertEqual(set(self.run_jobs(force=True)), JOB_NAMES)

    def test_expires_stale_pending_payments(self):
        order = Order.objects.create(buyer=make_user(), total=Decimal("10.00"))
        old = Payment.objects.create(order=order, provider="demo", amount=1, currency="USD")
        Payment.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))
        fresh = Payment.objects.create(order=order, provider="demo", amount=1, currency="USD")

        self.assertEqual(scheduler.expire_stale_payments(), "1 payment(s) expired")
        old.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual((old.status, fresh.status), ("cancelled", "pending"))

    def test_command_once(self):
        out = StringIO()
        with quiet_rates():
            call_command("run_scheduler", "--once", stdout=out)
        self.assertIn("update_exchange_rates: done", out.getvalue())

    def test_command_loop_stops_on_signal(self):
        from main.management.commands.run_scheduler import Command

        command = Command(stdout=StringIO())

        def stop_after_first_round(results):
            command.stopping = True

        with (
            quiet_rates(),
            mock.patch.object(command, "report", side_effect=stop_after_first_round),
        ):
            command.handle(poll=1)
        self.assertEqual(JobRun.objects.count(), 3)
