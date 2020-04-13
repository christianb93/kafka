#!/usr/bin/python3

import config
import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", 
                    type=str,
                    help="Location of a configuration file in YAML format")
    args=parser.parse_args()
    return args

args=get_args()
print(config.Config(args.config).get_bootstrap_broker_url()[0])