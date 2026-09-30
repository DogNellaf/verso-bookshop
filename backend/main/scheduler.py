"""Periodic jobs, run by ``python manage.py run_scheduler``.

The scheduler is a separate container in docker-compose. Each job records its
last run in the ``JobRun`` table, which the admin shows. Claiming a job locks
its row, so two scheduler processes never run the same job at once.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from main.models import JobRun, Payment

logger = logging.getLogger(__name__)


def update_exchange_rates():
    out = StringIO()
    call_command("update_exchange_rates", stdout=out)
    return out.getvalue().strip()


def retry_refunds():
    from main.payments.services import refund_payment

    owed = Payment.objects.filter(needs_refund=True, status=Payment.Status.SUCCEEDED)
    results = [refund_payment(pk).status for pk in owed.values_list("pk", flat=True)]
    done = results.count(Payment.Status.REFUNDED)
    return f"{done} of {len(results)} refund(s) sent"


def expire_stale_payments():
    """Pending payments nobody finished. Stripe sessions expire after a day too."""
    cutoff = timezone.now() - timedelta(hours=settings.PAYMENT_TIMEOUT_HOURS)
    count = Payment.objects.filter(status=Payment.Status.PENDING, created_at__lt=cutoff).update(
        status=Payment.Status.CANCELLED, failure_reason="Expired without payment."
    )
    return f"{count} payment(s) expired"


@dataclass(frozen=True)
class Job:
    name: str
    every: timedelta
    run: callable


def jobs():
    return [
        Job(
            "update_exchange_rates",
            timedelta(hours=settings.EXCHANGE_RATES_INTERVAL_HOURS),
            update_exchange_rates,
        ),
        Job("retry_refunds", timedelta(minutes=15), retry_refunds),
        Job("expire_stale_payments", timedelta(hours=1), expire_stale_payments),
    ]


def claim(job, now, force=False):
    """Mark the job as started if it is due. Returns False when it isn't."""
    with transaction.atomic():
        run, _ = JobRun.objects.select_for_update().get_or_create(name=job.name)
        if not force and run.last_started and now - run.last_started < job.every:
            return False
        run.last_started = now
        run.save(update_fields=["last_started"])
        return True


def run_due_jobs(now=None, force=False):
    """Run every job that is due. Returns {name: succeeded}."""
    now = now or timezone.now()
    results = {}
    for job in jobs():
        if not claim(job, now, force=force):
            continue
        try:
            message, succeeded = job.run() or "", True
        except Exception as exc:  # one failing job must not stop the others
            logger.exception("Scheduled job %s failed", job.name)
            message, succeeded = f"{type(exc).__name__}: {exc}", False
        JobRun.objects.filter(name=job.name).update(
            last_finished=timezone.now(), succeeded=succeeded, message=message[:2000]
        )
        logger.info("Job %s %s. %s", job.name, "done" if succeeded else "failed", message)
        results[job.name] = succeeded
    return results
