import ckan.plugins.toolkit as toolkit
import ckanext.qdes.jobs as jobs
import click
import logging


log = logging.getLogger(__name__)

@click.command(u"ckan-job-worker-monitor")
def ckan_worker_job_monitor():
    try:
        toolkit.enqueue_job(jobs.ckan_worker_job_monitor, title='CKAN job worker monitor')
        click.secho(u"CKAN job worker monitor added to worker queue", fg=u"green")
    except Exception as e:
        log.error(e)


def get_commands():
    return [ckan_worker_job_monitor]