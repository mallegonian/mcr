# libmcr.py
# This file is part of the MCR project
# Copyright 2013 Trevor Bergeron, et al., all rights reserved

import os
import configparser

libmcr_version="0.1-dev"

class Server(object):
    """ A minecraft server """

    def __init__(self,name="",user=""):
        self.name=name
        self.user=user
        self.config=self.__loadconfig(name,user)

    def __loadconfig(self,name="",user=""):
        """
        name: server name
        user: username for cfg (and running)
        """
        class MyConfigParser(configparser.ConfigParser):
            def as_dict(self):
                d = dict(self._sections)
                for k in d:
                    d[k] = dict(self._defaults, **d[k])
                    d[k].pop('__name__', None)
                return d
        mycfgp=MyConfigParser()
        name = name if name else "default"
        mycfgp.read(os.path.expanduser("~"+user)+"/.config/mcr/"+name)
        allconfigs=mycfgp.as_dict()
        if len(allconfigs)<1:
            print("No or empty config file for this server. See \"mcr help config\".")
            return
        if not name in allconfigs:
            print("No server section found for \"",name,"\".",sep="")
            return
        return allconfigs[name]

    def stop():
        print("Not implemented")

    def start():
        print("Not implemented")

    def status():
        print("Not implemented")

    def send():
        print("Not implemented")

    def backup():
        print("Not implemented")

def getservers(user=""):
    """ Create a dictionary of all servers for a(=this) user """
    servers={}
    for svname in os.listdir(os.path.expanduser("~"+user)+"/.config/mcr/"):
        servers[svname]=Server(svname,user)
    return servers

