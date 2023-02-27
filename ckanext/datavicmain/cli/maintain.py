from __future__ import annotations

import click
import datetime
import logging
from typing import Union

from sqlalchemy.exc import SQLAlchemyError

import ckan.model as model


log = logging.getLogger(__name__)


@click.group()
def maintain():
    """Portal maintenance tasks"""
    pass


@maintain.command(u"ckan-resources-date-cleanup")
def ckan_iar_resource_date_cleanup():
    """Fix resources with invalid date range. One-time task.
    """
    resource_query = model.Session.query(model.Resource)
    query = resource_query.filter(
        (model.Resource.state == model.core.State.ACTIVE))

    for resource in query:
        click.secho(f"Processing resource {resource.name}", fg=u"green")

        if not __fix_resource_extras(resource.extras):
            continue
        try:
            resource_query.filter(model.Resource.id == resource.id ).update(
                {"extras": resource.extras})
            model.Session.commit()
            click.secho(f"Fixed date issues for resource {resource.name}", fg=u"green")
        except SQLAlchemyError:
            click.secho(f"DB Error: Failed to fix  resource {resource.name}", fg=u"red")
            model.Session.rollback()


def __fix_resource_extras(extras: dict[str, Union[int, bool, str]]):
    """Make the invalid date field value to None.
    
    :param extras: resource extras field dict
    :returns: if updated the extras then returns True, else None
    """
    date_fields = ['period_end', 'period_start', 'release_date']
    
    old_extras = extras.copy()

    for field in date_fields:
        if not extras.get(field):
            continue
        if not __valid_date(extras.get(field)):
            click.secho(f"Found invalid date for {field}: {extras.get(field)}", fg=u"red")
            extras[field] = None

    if old_extras != extras:
        return True


def __valid_date(date:str) -> bool:
    """Validates given date.

    :param date: input date
    :returns: True or False based on validation
    """
    date_format = '%Y-%m-%d'
    try:
        dateObject = datetime.datetime.strptime(date, date_format)
    except ValueError:
        return False
    
    return True