#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui import watolib
from cmk.gui.watolib.services import (StartDiscoveryRequest, DiscoveryOptions, get_check_table,
                                      checkbox_name)
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict
from cmk.gui.plugins.openapi.restful_objects import (endpoint_schema, response_schemas)
from cmk.gui.plugins.openapi.restful_objects.constructors import (domain_object, object_property)

SERVICE_DISCOVERY_STATES = {
    "undecided": "new",
    "vanished": "vanished",
    "monitored": "old",
    "ignored": "ignored",
    "removed": "removed",
    "manual": "manual",
    "active": "active",
    "custom": "custom",
    "clustered_monitored": "clustered_old",
    "clustered_undecided": "clustered_new",
    "clustered_vanished": "clustered_vanished",
    "clustered_ignored": "clustered_ignored",
    "active_ignored": "active_ignored",
    "custom_ignored": "custom_ignored",
    "legacy": "legacy",
    "legacy_ignored": "legacy_ignored"
}

DISCOVERY_HOST = ParamDict.create(
    'host',
    schema_pattern="[a-zA-Z][a-zA-Z0-9_-]+",
    location='query',
    description=('Optionally the hostname for which a certain agent has '
                 'been configured. If omitted you may only download this agent if you '
                 'have the rights for all agents.'),
    example='example.com',
    required=True)

DISCOVERY_SOURCE_STATE = ParamDict.create(
    'discovery_state',
    location='query',
    description=('The discovery state of the services. May be one of the following: ' +
                 ', '.join(sorted(SERVICE_DISCOVERY_STATES.keys()))),
    schema_pattern='|'.join(sorted(SERVICE_DISCOVERY_STATES.keys())),
    example='monitored',
    required=False)


@endpoint_schema('/domain-types/service/collections/services',
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.DomainObject,
                 parameters=[DISCOVERY_HOST, DISCOVERY_SOURCE_STATE])
def show_services(params):
    """Show services of specific state"""
    host = watolib.Host.host(params["host"])
    discovery_request = StartDiscoveryRequest(
        host=host,
        folder=host.folder(),
        options=DiscoveryOptions(action='',
                                 show_checkboxes=False,
                                 show_parameters=False,
                                 show_discovered_labels=False,
                                 show_plugin_names=False,
                                 ignore_errors=True),
    )
    discovery_result = get_check_table(discovery_request)
    return _serve_services(host, discovery_result.check_table, params["discovery_state"])


def _serve_services(host, discovered_services, discovery_state):
    response = Response()
    response.set_data(
        json.dumps(serialize_service_discovery(host, discovered_services, discovery_state)))
    response.set_content_type('application/json')
    return response


SERVICE_STATE = {0: "OK", 1: "WARN", 2: "CRIT"}


def serialize_service_discovery(host, discovered_services, discovery_state):
    members = {}
    for table_source, check_type, _checkgroup, item, _paramstring, _params, descr, \
        _service_state, _output, _perfdata, _service_labels in discovered_services:
        if table_source == SERVICE_DISCOVERY_STATES[discovery_state]:
            service_hash = checkbox_name(check_type, item)
            members[service_hash] = {
                "service_name": descr,
                "check_plugin_name": check_type,
                "state": object_property(
                    name=descr,
                    title="The service is currently %s" % discovery_state,
                    value=table_source,
                    prop_format='string',
                    base='',
                    linkable=False,
                )
            }

    return domain_object(
        domain_type='service_discovery',
        identifier='%s-services-%s' % (host.ident(), "wato"),
        title='Services discovery',
        members=members,
        extensions={},
    )