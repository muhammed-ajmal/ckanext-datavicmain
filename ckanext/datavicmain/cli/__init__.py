import click
import logging

from ckan.plugins.toolkit import enqueue_job
from ckanext.datavicmain import jobs

from . import maintain

log = logging.getLogger(__name__)


@click.group()
def dcmain():
    """ckanext-datavicmain management commands."""
    pass


@dcmain.command(u"ckan-job-worker-monitor")
def ckan_worker_job_monitor():
    try:
        enqueue_job(jobs.ckan_worker_job_monitor, title="CKAN job worker monitor")
        click.secho(u"CKAN job worker monitor added to worker queue", fg=u"green")
    except Exception as e:
        log.error(e)


dcmain.add_command(maintain.maintain)


def get_commands():
    return [dcmain]
