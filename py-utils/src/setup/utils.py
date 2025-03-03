#!/bin/env python3

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

import os
import glob
import json
import errno
from pathlib import Path

from cortx.utils import errors
from cortx.utils import const
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from cortx.utils.common import SetupError
from cortx.utils.errors import TestFailed
from cortx.utils.validator.v_pkg import PkgV
from cortx.utils.process import SimpleProcess
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_confkeys import ConfKeysV
from cortx.utils.service.service_handler import Service
from cortx.utils.common import CortxConf


class Utils:
    """ Represents Utils and Performs setup related actions """

    # Utils private methods


    @staticmethod
    def _delete_files(files: list):
        """
        Deletes the passed list of files

        Args:
            files ([str]): List of files to be deleted

        Raises:
            SetupError: If unable to delete file
        """
        for each_file in files:
            if os.path.exists(each_file):
                try:
                    os.remove(each_file)
                except OSError as e:
                    raise SetupError(e.errno, "Error deleting file %s, \
                        %s", each_file, e)

    @staticmethod
    def _get_utils_path() -> str:
        """ Gets install path from cortx.conf and returns utils path """
        install_path = CortxConf.get(key='install_path')
        if not install_path:
            local_storage_path = CortxConf.get_storage_path('local')
            config_url = "%s://%s" % ('json', \
                os.path.join(local_storage_path, 'utils/conf/cortx.conf'))
            raise SetupError(errno.EINVAL, "install_path not found in %s",\
                config_url)
        return install_path

    def _set_to_conf_file(key, value):
        """ Add key value pair to cortx.conf file """
        CortxConf.set(key, value)
        CortxConf.save()

    # Utils private methods
    @staticmethod
    def _get_from_conf_file(key) -> str:
        """ Fetch and return value for the key from cortx.conf file """
        val = CortxConf.get(key=key)

        if not val:
            local_storage_path = CortxConf.get_storage_path('local')
            config_url = "%s://%s" % ('json', \
                os.path.join(local_storage_path, 'utils/conf/cortx.conf'))
            raise SetupError(errno.EINVAL, "Value for key: %s, not found in \
                %s", key, config_url)

        return val

    @staticmethod
    def _copy_cluster_map(config_path: str):
        Conf.load('cluster', config_path, skip_reload=True)
        cluster_data = Conf.get('cluster', 'node')
        for _, node_data in cluster_data.items():
            hostname = node_data.get('hostname')
            node_name = node_data.get('name')
            Conf.set('cluster', f'cluster>{node_name}', hostname)
        Conf.save('cluster')

    @staticmethod
    def _configure_rsyslog():
        """
        Restart rsyslog service for reflecting supportbundle rsyslog config
        """
        try:
            Log.info("Restarting rsyslog service")
            service_obj = Service("rsyslog.service")
            service_obj.restart()
        except Exception as e:
            Log.warn(f"Error in rsyslog service restart: {e}")

    @staticmethod
    def validate(phase: str):
        """ Perform validtions """

        # Perform RPM validations
        pass

    @staticmethod
    def post_install(config_path: str):
        """ Performs post install operations """
        # Check required python packages
        install_path = Utils._get_from_conf_file('install_path')
        utils_path = install_path + '/cortx/utils'
        with open(f"{utils_path}/conf/python_requirements.txt") as file:
            req_pack = []
            for package in file.readlines():
                pack = package.strip().split('==')
                req_pack.append(f"{pack[0]} ({pack[1]})")
        try:
            with open(f"{utils_path}/conf/python_requirements.ext.txt") as extfile :
                for package in extfile.readlines():
                    pack = package.strip().split('==')
                    req_pack.append(f"{pack[0]} ({pack[1]})")
        except Exception:
             Log.info("Not found: "+f"{utils_path}/conf/python_requirements.ext.txt")

        PkgV().validate(v_type='pip3s', args=req_pack)
        default_sb_path = '/var/log/cortx/support_bundle'
        Utils._set_to_conf_file('support>local_path', default_sb_path)
        os.makedirs(default_sb_path, exist_ok=True)

        post_install_template_index = 'post_install_index'
        Conf.load(post_install_template_index, config_path)

        machine_id = Conf.machine_id
        key_list = [f'node>{machine_id}>hostname', f'node>{machine_id}>name']
        ConfKeysV().validate('exists', post_install_template_index, key_list)

        #set cluster nodename:hostname mapping to cluster.conf (needed for Support Bundle)
        Utils._copy_cluster_map(config_path)

        return 0

    @staticmethod
    def config(config_path: str):
        """Performs configurations."""
        # Load required files
        config_template_index = 'config'
        Conf.load(config_template_index, config_path)
        # Configure log_dir for utils
        log_dir = CortxConf.get_storage_path('log')
        if log_dir is not None:
            CortxConf.set('log_dir', log_dir)
            CortxConf.save()

        # set cluster nodename:hostname mapping to cluster.conf
        Utils._copy_cluster_map(config_path)
        Utils._configure_rsyslog()

        # get shared storage from cluster.conf and set it to cortx.conf
        shared_storage = CortxConf.get_storage_path('shared', none_allowed=True)
        if shared_storage:
            Utils._set_to_conf_file('support>shared_path', shared_storage)

        # temporary fix for a common message bus log file
        # The issue happend when some user other than root:root is trying
        # to write logs in these log dir/files. This needs to be removed soon!
        log_dir = CortxConf.get('log_dir', '/var/log')
        utils_log_dir = CortxConf.get_log_path(base_dir=log_dir)
        #message_bus
        os.makedirs(os.path.join(utils_log_dir, 'message_bus'), exist_ok=True)
        os.chmod(os.path.join(utils_log_dir, 'message_bus'), 0o0777)
        Path(os.path.join(utils_log_dir,'message_bus/message_bus.log')) \
            .touch(exist_ok=True)
        os.chmod(os.path.join(utils_log_dir,'message_bus/message_bus.log'), 0o0666)
        #iem
        os.makedirs(os.path.join(utils_log_dir, 'iem'), exist_ok=True)
        os.chmod(os.path.join(utils_log_dir, 'iem'), 0o0777)
        Path(os.path.join(utils_log_dir, 'iem/iem.log')).touch(exist_ok=True)
        os.chmod(os.path.join(utils_log_dir, 'iem/iem.log'), 0o0666)
        return 0

    @staticmethod
    def init(config_path: str):
        """ Perform initialization """
        # Create message_type for Event Message
        from cortx.utils.message_bus import MessageBus, MessageBusAdmin
        from cortx.utils.message_bus.error import MessageBusError
        try:
            # Read the config values
            Conf.load('config', config_path, skip_reload=True)
            message_bus_backend = Conf.get('config', \
                'cortx>utils>message_bus_backend')
            message_server_endpoints = Conf.get('config', \
                f'cortx>external>{message_bus_backend}>endpoints')
            MessageBus.init(message_server_endpoints)
            admin = MessageBusAdmin(admin_id='register')
            admin.register_message_type(message_types=['IEM', \
                'audit_messages'], partitions=1)
        except MessageBusError as e:
            if 'TOPIC_ALREADY_EXISTS' not in e.desc:
                raise SetupError(e.rc, "Unable to create message_type. %s", e)

        return 0

    @staticmethod
    def test(config_path: str, plan: str):
        """ Perform configuration testing """
        # Runs cortx-py-utils unittests as per test plan
        try:
            Log.info("Validating cortx-py-utils-test rpm")
            PkgV().validate('rpms', ['cortx-py-utils-test'])
            install_path = Utils._get_from_conf_file('install_path')
            utils_path = install_path + '/cortx/utils'
            import cortx.utils.test as test_dir
            plan_path = os.path.join(os.path.dirname(test_dir.__file__), \
                'plans/', plan + '.pln')
            Log.info("Running test plan: %s", plan)
            cmd = "%s/bin/run_test -c %s -t %s" %(utils_path, config_path, plan_path)
            _output, _err, _rc = SimpleProcess(cmd).run(realtime_output=True)
            if _rc != 0:
                Log.error("Py-utils Test Failed")
                raise TestFailed("Py-utils Test Failed. \n Output : %s "\
                    "\n Error : %s \n Return Code : %s" %(_output, _err, _rc))
        except VError as ve:
            Log.error("Failed at package Validation: %s", ve)
            raise SetupError(errno.EINVAL, "Failed at package Validation:"\
                " %s", ve)
        return 0

    @staticmethod
    def reset(config_path: str):
        """Remove/Delete all the data/logs that was created by user/testing."""
        from cortx.utils.message_bus.error import MessageBusError
        try:
            from cortx.utils.message_bus import MessageBusAdmin, MessageBus
            from cortx.utils.message_bus import MessageProducer
            Conf.load('config', config_path, skip_reload=True)
            message_bus_backend = Conf.get('config', \
                'cortx>utils>message_bus_backend')
            message_server_endpoints = Conf.get('config', \
                f'cortx>external>{message_bus_backend}>endpoints')
            MessageBus.init(message_server_endpoints)
            mb = MessageBusAdmin(admin_id='reset')
            message_types_list = mb.list_message_types()
            if message_types_list:
                for message_type in message_types_list:
                    producer = MessageProducer(producer_id=message_type, \
                        message_type=message_type, method='sync')
                    producer.delete()

        except MessageBusError as e:
            raise SetupError(e.rc, "Can not reset Message Bus. %s", e)
        except Exception as e:
            raise SetupError(errors.ERR_OP_FAILED, "Internal error, can not \
                reset Message Bus. %s", e)
        # Clear the logs
        utils_log_path = CortxConf.get_log_path()
        if os.path.exists(utils_log_path):
            cmd = "find %s -type f -name '*.log' -exec truncate -s 0 {} +" % utils_log_path
            cmd_proc = SimpleProcess(cmd)
            _, stderr, rc = cmd_proc.run()
            if rc != 0:
                raise SetupError(errors.ERR_OP_FAILED, \
                    "Can not reset log files. %s", stderr)
        return 0

    @staticmethod
    def cleanup(pre_factory: bool, config_path: str):
        """Remove/Delete all the data that was created after post install."""

        # delete message_types
        from cortx.utils.message_bus.error import MessageBusError
        try:
            from cortx.utils.message_bus import MessageBus, MessageBusAdmin
            Conf.load('config', config_path, skip_reload=True)
            message_bus_backend = Conf.get('config', \
                'cortx>utils>message_bus_backend')
            message_server_endpoints = Conf.get('config', \
                f'cortx>external>{message_bus_backend}>endpoints')
            MessageBus.init(message_server_endpoints)
            mb = MessageBusAdmin(admin_id='cleanup')
            message_types_list = mb.list_message_types()
            if message_types_list:
                mb.deregister_message_type(message_types_list)
        except MessageBusError as e:
            raise SetupError(e.rc, "Can not cleanup Message Bus. %s", e)
        except Exception as e:
            raise SetupError(errors.ERR_OP_FAILED, "Can not cleanup Message  \
                Bus. %s", e)

        if pre_factory:
            # deleting all log files as part of pre-factory cleanup
            utils_log_path = CortxConf.get_log_path()
            cortx_utils_log_regex = f'{utils_log_path}/**/*.log'
            log_files = glob.glob(cortx_utils_log_regex, recursive=True)
            Utils._delete_files(log_files)

        return 0

    @staticmethod
    def upgrade(config_path: str):
        """Perform upgrade steps."""
        # ToDo - in future, for utils/message server config changes may be
        # required during upgrade phase.
        # Currently no config changes required.
        return 0

    @staticmethod
    def pre_upgrade(level: str):
        """ pre upgrade hook for node and cluster level """
        if level == 'node':
            # TODO Perform corresponding actions for node
            pass
        elif level == 'cluster':
            # TODO Perform corresponding actions for cluster
            pass
        return 0

    @staticmethod
    def post_upgrade(level: str):
        """ post upgrade hook for node and cluster level """
        if level == 'node':
            # TODO Perform corresponding actions for node
            pass
        elif level == 'cluster':
            # TODO Perform corresponding actions for cluster
            pass
        return 0
