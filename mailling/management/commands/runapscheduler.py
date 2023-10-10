import logging

from django.conf import settings

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
import smtplib

from mailling.models import Logs, Message, Mailling
from mailling.services import send_message_email

logger = logging.getLogger(__name__)


def my_job(mailling):
    try:
        send_message_email(mailling)
        Logs.objects.create(status_try='Success', mailling_id=mailling)
    except Exception as error:
        Logs.objects.create(status_try='Fail', answer=error, mailling_id=mailling)

@util.close_old_connections
def delete_old_job_executions(max_age=604_800):

    """
    This job deletes APScheduler job execution entries older than `max_age` from the database.
    It helps to prevent the database from filling up with old historical records that are no
    longer useful.

    :param max_age: The maximum length of time to retain historical job execution records.
                    Defaults to 7 days.
    """
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")
        for mailling in Mailling.objects.all():
            if mailling.status == 'created' and mailling.periodicity == 'DAILY':
                scheduler.add_job(
                    my_job,
                    trigger=CronTrigger(minute='*/5'),
                    id="my_job",  # The `id` assigned to each job MUST be unique
                    max_instances=1,
                    replace_existing=True,
                    args=[mailling],
                    )
                logger.info("Added job 'my_job'.")
            elif mailling.status == 'created' and mailling.periodicity == 'WEEKLY':
                scheduler.add_job(
                    my_job,
                    trigger=CronTrigger(day_of_week="mon", hour="00", minute="00"),
                    id="my_job",  # The `id` assigned to each job MUST be unique
                    max_instances=1,
                    replace_existing=True,
                    args=[mailling],
                )
                logger.info("Added job 'my_job'.")
            else:
                scheduler.add_job(
                    my_job,
                    trigger=CronTrigger(day="1", hour="00", minute="00"),
                    id="my_job",  # The `id` assigned to each job MUST be unique
                    max_instances=1,
                    replace_existing=True,
                    args=[mailling],
                )
                logger.info("Added job 'my_job'.")

            if mailling.status == 'started':
                if mailling.date_end < timezone.localtime(timezone.now()):
                    mailling.status = 'closed'
                    scheduler.add_job(
                        delete_old_job_executions,
                        trigger=CronTrigger(
                            day_of_week="mon", hour="00", minute="00"
                        ),  # Midnight on Monday, before start of the next work week.
                        id="delete_old_job_executions",
                        max_instances=1,
                        replace_existing=True,
                    )
                    logger.info(
                        "Added weekly job: 'delete_old_job_executions'."
                    )
        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

# trigger=CronTrigger(hour='*/24', minute='*', second='*', )