import config
import requester.config


def get_config(name):
    return requester.config.__REQUESTER_CONFIG__.get(name, None)