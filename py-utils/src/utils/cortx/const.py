#!/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

from enum import Enum

class Const(Enum):
    """Enum class to define constants for components and service names."""

    # Active Components
    COMPONENT_UTILS        = 'utils'
    COMPONENT_MOTR         = 'motr'
    COMPONENT_HARE         = 'hare'
    COMPONENT_S3           = 's3'
    COMPONENT_HA           = 'ha'
    COMPONENT_CSM          = 'csm'
    COMPONENT_CCLIENT      = 'cclient'

    # Active Services
    SERVICE_MOTR_IO         = 'io'
    SERVICE_MOTR_FSM        = 'fsm'
    SERVICE_HARE_HAX        = 'hax'
    SERVICE_S3_SERVER       = 's3server'
    SERVICE_S3_HAPROXY      = 'haproxy'
    SERVICE_S3_AUTHSERVER   = 'authserver'
    SERVICE_S3_BGWORKER     = 'bgworker'
    SERVICE_S3_BGSCHEDULER  = 'bgscheduler'
    SERVICE_CSM_AGENT       = 'agent'
    SERVICE_UTILS_MESSAGE   = 'message'
    SERVICE_CCLIENT         = 'cclient_service'

    # Deprecated services
    SERVICE_S3_IO          = 'io'
    SERVICE_S3_AUTH        = 'auth'
    SERVICE_S3_BGCONSUMER  = 'bg_consumer'
    SERVICE_S3_BGPRODUCER  = 'bg_producer'
    SERVICE_S3_OPENLDAP    = 'openldap'
