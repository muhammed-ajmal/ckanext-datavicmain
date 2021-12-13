import os
import requests
import logging

log = logging.getLogger(__name__)

betteruptime_ulr = os.environ.get('JOBWORKER_MONITOR_URL', None)

def ckan_worker_job_monitor():
    try:
        log.info(f'Sending notification to healthchecks for CKAN worker job monitor')
        requests.get(betteruptime_ulr, timeout=10)
        log.info(f'Successfully sent notification to healthchecks for CKAN worker job monitor')
    except requests.RequestException as e:
        log.error(f'Failed to send ckan worker job monitor notification to healthchecks')
        log.error(str(e))