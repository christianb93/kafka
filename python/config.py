import os
import sys
import yaml



class  Config:

    def __init__(self,config_path=None):
        if config_path is None:
            #
            # Determine the repository root directory
            #
            pathname = os.path.dirname(sys.argv[0]) 
            rootdir=os.path.abspath(pathname+"/..")
            self._config_path=rootdir+"/.state/config.yaml"
        else:
            self._config_path=config_path
        #
        # Read and cache configuration
        self._config=self._read_config_yaml()

    def _read_config_yaml(self):
        #
        # Import broker configuration
        #
        with open(self._config_path) as config_yaml:
            config = yaml.load(config_yaml,Loader=yaml.CLoader)
        return config

    def get_broker_configuration(self):
        return self._config['brokers']

    def get_bootstrap_broker_url(self):
        broker_config=self.get_broker_configuration()
        bootstrap_broker = []
        for broker in broker_config:
            bootstrap_broker.append(broker['ip']+":"+broker['port'])
        return bootstrap_broker

    def get_ssl_config(self):
        return self._config['ssl_config']


    def get_producer_config(self):
        producer_config=dict()
        broker_url=self.get_bootstrap_broker_url()
        producer_config['bootstrap_servers']=broker_url
        producer_config['security_protocol']="SSL"
        producer_config.update(self.get_ssl_config())
        return producer_config
