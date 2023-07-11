import os

import requests

from base64 import b64encode
from datetime import datetime

from .model import Client


class AsusWRT:
    _USER_AGENT = 'asusrouter-Android-DUTUtil-1.0.0.3.58-163'
    _CONTENT_TYPE = 'application/x-www-form-urlencoded'

    def __init__(self):
        """Initialize AsusWRT class with url, username, and password."""
        self._url = None
        self._username = None
        self._password = None
        self._asus_token_timestamp = None
        self._custom_clients = None
        self.set_from_env_variable('_url', 'URL')
        self.set_from_env_variable('_username', 'USERNAME')
        self.set_from_env_variable('_password', 'PASSWORD')
        self._url = f"http://{self._url}"
        self._session = requests.Session()
        self.refresh_asus_token()

    def is_asus_token_set(self):
        """Return True if authentication token is present, else False."""
        return 'asus_token' in self._session.cookies.keys()

    def is_asus_token_valid(self):
        """Return True if the asus token is not older than 60 minutes, else False."""
        return (datetime.now() - self._asus_token_timestamp).seconds < 60 * 60

    def refresh_asus_token(self):
        """Refresh authentication token."""
        self.request(
            'POST',
            '/login.cgi',
            {
                'login_authorization':
                    b64encode(('%s:%s' % (self._username, self._password)).encode('utf-8')).decode('utf-8')
            }
        )
        self._asus_token_timestamp = datetime.now()

    def logout(self):
        """Logout from the session."""
        self.request('GET', '/Logout.asp')
        self._session = requests.Session()

    def get_sys_info(self):
        """Return system information as a dictionary."""
        response = self.get('nvram_get(productid);nvram_get(firmver);nvram_get(buildno);nvram_get(extendno)')
        return {
            'model':    response.get('productid'),
            'firmware': '%s_%s_%s' % (response.get('firmver'), response.get('buildno'), response.get('extendno'))
        }

    def get_cpu_mem_info(self):
        """Return CPU and memory usage information as a dictionary."""
        response = self.get('cpu_usage(appobj);memory_usage(appobj);')
        return {
            'cpu':    response['cpu_usage'],
            'memory': {
                'total': response['memory_usage']['mem_total'],
                'used':  response['memory_usage']['mem_used'],
                'free':  response['memory_usage']['mem_free']
            }
        }

    def get_wan_state(self):
        """Return the WAN state."""
        return self.get('wanlink_state(appobj)')

    def get_online_clients(self):
        """Return a list of online clients."""

        def get_client(mac):
            return next((client for client in clients if client.mac == mac), None)

        def update_interface(interface, interface_name):
            interface_clients = response.get('wl_sta_list_%s' % interface, {})
            for key, val in interface_clients.items():
                client = get_client(key)
                if client:
                    client.interface = interface_name
                    client.rssi = val.get('rssi')

        def update_custom():
            self.parse_custom_clientlist(response.get('custom_clientlist', ''))
            for key, val in self._custom_clients.items():
                client = get_client(key)
                if client:
                    client.alias = val.get('alias')

        response = self.get(
            'get_clientlist(appobj);'
            'wl_sta_list_2g(appobj);'
            'wl_sta_list_5g(appobj);'
            'wl_sta_list_5g_2(appobj);'
            'nvram_get(custom_clientlist)'
        )

        clients = response.get('get_clientlist', {})
        clients.pop('maclist', None)
        clients.pop('ClientAPILevel', None)
        clients = list(map(Client, list(clients.values())))

        update_interface('2g', '2GHz')
        update_interface('5g', '5GHz')
        update_interface('5g_2', '5GHz-2')
        update_custom()

        return clients

    def parse_custom_clientlist(self, clientlist):
        """Parse user set metadata for clients and return the clientlist."""
        self._custom_clients = clientlist.replace('&#62', '>').replace('&#60', '<').split('<')
        self._custom_clients = [client.split('>') for client in clientlist]
        self._custom_clients = {
            client[1]: {'alias': client[0], 'group': client[2], 'type': client[3], 'callback': client[4]} for
            client in clientlist if len(client) == 6
        }

    def restart_service(self, service):
        """Restart a given service."""
        return self.apply({'action_mode': 'apply', 'rc_service': service})

    def get(self, payload):
        """Perform a GET request with given payload and return the response as JSON."""
        response = self.request('POST', '/appGet.cgi', {'hook': payload})
        return response.json()

    def apply(self, payload):
        """Perform an APPLY request with given payload and return the response as JSON."""
        return self.request('POST', '/applyapp.cgi', payload).json()

    def request(self, method, path, payload=None):
        """
        Make REST API call

        :param str method: http verb
        :param str path: api path
        :param dict payload: request payload
        :return: the REST response
        """

        return self._session.request(
            method=method.upper(),
            url=self._url + path,
            headers={
                'User-Agent':   self._USER_AGENT,
                'Content-Type': self._CONTENT_TYPE
            },
            data=payload,
            verify=False
        )

    def set_from_env_variable(self, att, var_name):
        """Fetch a given environment variable. Raise an exception if it is not found."""
        value = os.environ.get(var_name)
        if value is None:
            raise Exception(f"The environment variable {var_name} is not set.")

        setattr(self, att, value)
