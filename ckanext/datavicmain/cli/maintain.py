from __future__ import annotations

import click
import datetime
import logging
from typing import Union

import ckan.model as model
import ckan.plugins.toolkit as tk


log = logging.getLogger(__name__)


@click.group()
def maintain():
    """Portal maintenance tasks"""
    pass


@maintain.command("ckan-resources-date-cleanup")
def ckan_iar_resource_date_cleanup():
    """Fix resources with invalid date range. One-time task."""
    resource_query = model.Session.query(model.Resource)
    query = resource_query.filter((model.Resource.state == model.core.State.ACTIVE))

    patch = tk.get_action("package_patch")
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})

    package_list = tk.get_action("current_package_list_with_resources")(
        {"user": user["name"]}, {}
    )

    for package in package_list:
        fix_available = False
        click.secho(f"Processing resources in {package['name']}", fg="green")

        for resource in package.get("resources"):
            if _fix_improper_date_values(resource):
                fix_available = True

        if not fix_available:
            continue
        try:
            patch(
                {"user": user["name"]},
                {"id": package["id"], "resources": package.get("resources")},
            )
            click.secho(
                f"Fixed date issues for resources in {package['name']}", fg="green"
            )
        except tk.ValidationError as e:
            click.secho(f"Failed to fix  resources {package['name']}: {e}", fg="red")


def _fix_improper_date_values(resource: dict[str, Union[int, bool, str]]):
    """Make the invalid date field value to None.

    :param resource: resource dict
    :returns: if updated the resource then returns True, else None
    """
    date_fields = ["period_end", "period_start", "release_date"]

    old_resource = resource.copy()

    for field in date_fields:
        if not resource.get(field):
            continue
        if not _valid_date(resource.get(field)):
            click.secho(
                f"Found invalid date for {field} in {resource['name']}: {resource.get(field)}",
                fg="red",
            )
            resource[field] = None

    if old_resource != resource:
        return True


def _valid_date(date: str) -> bool:
    """Validates given date.

    :param date: input date
    :returns: True or False based on validation
    """
    date_format = "%Y-%m-%d"
    try:
        dateObject = datetime.datetime.strptime(date, date_format)
    except ValueError:
        return False

    return True
