import os
import sys
import yaml



class  Config:

    def __init__(self):
        self._config=self._read_config_yaml()

    def _read_config_yaml(self):
        #
        # Determine the repository root directory
        #
        pathname = os.path.dirname(sys.argv[0]) 
        rootdir=os.path.abspath(pathname+"/..")
        #
        # Import broker configuration
        #
        with open(rootdir+"/.state/config.yaml") as config_yaml:
            config = yaml.load(config_yaml,Loader=yaml.CLoader)
        return config

    def get_broker_configuration(self):
        return self._config['brokers']

    def get_bootstrap_broker_url(self):
        broker_config=self.get_broker_configuration()
        bootstrap_broker = broker_config[0]
        return bootstrap_broker['ip']+":"+bootstrap_broker['port']

    def get_ssl_config(self):
        return self._config['ssl_config']


