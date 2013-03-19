"""
libmcr.py
This file is part of the MCR project
Copyright 2013 Trevor Bergeron & Sean Buckley, all rights reserved
"""

import configparser
from datetime import datetime
import logging
import os
from shutil import copytree, ignore_patterns
import subprocess
import sys
import time

libmcr_version = "0.1-dev"

logger = logging.getLogger("libmcr")
# At the moment these cause double logging
#ch = logging.StreamHandler()
#formatter = logging.Formatter(
#    '%(asctime)s %(name)s [%(levelname)s] %(message)s')
#ch.setFormatter(formatter)
#logger.addHandler(ch)


class Server(object):
    """ A minecraft server """

    (
        ERROR_NONE,
        ERROR_GENERAL,
        ERROR_CONFIG,
        ERROR_NOT_RUNNING,
        ERROR_NOT_IMPLEMENTED
        ) = (0,1,2,3,99)

    javacmd="java"

    def __init__(self,name=None,user=None,configfile=None):
        name = name if name and type(name)==type(str) else "default"
        user = user if user and type(user)==type(str) else ""
        if configfile: # specified: check existence
            if not os.path.exists(configfile):
                configfile = os.getcwd()+configfile
                if not os.path.exists(configfile):
                    print("Could not find config file!")
        else: configfile = os.path.expanduser("~"+user)+"/.config/mcr"
        self.name = name
        self.user = user
        class MyConfigParser(configparser.ConfigParser):
            def as_dict(self):
                d = dict(self._sections)
                for k in d:
                    d[k] = dict(self._defaults, **d[k])
                    d[k].pop('__name__', None)
                return d
        mycfgp = MyConfigParser()
        mycfgp.read(configfile)
        allconfigs = mycfgp.as_dict()
        if len(allconfigs)<1:
            logger.error("No or empty config file, see \"mcr mkconfig\"")
            return(self.ERROR_CONFIG)
        if not name in allconfigs:
            logger.error("No server section found for \"",name,"\"")
            return(self.ERROR_CONFIG)
        config = allconfigs[name]
        logger.info("loaded cfg:"+str(config))
        
        if "dir" in config and os.path.exists(config["dir"]):
            self.directory = config["dir"]
        else:
            logger.error("required option \"dir\" invalid or not set")
            return(self.ERROR_CONFIG)
        self.tmuxname = config["tmuxname"] if "tmuxname" \
            in config and config["tmuxname"] else "mc"
        if "jar" in config:
            self.jar = config["jar"]
        else:
            logger.error("required option \"jar\" not found in config")
            return(self.ERROR_CONFIG)
        self.backupdir = config["backupdir"]
        self.backupremotetype = config["backupremotetype"]
        self.backupremoteaddress = config["backupremoteaddress"]

    def attach(self):
        if self.status():
            logger.error("server not running, can't attach")
            return(self.ERROR_NOT_RUNNING)
        # argv[0] is called binary name. Need os.execlp so tmux _replaces_ py.
        return(os.execlp("tmux","tmux","a","-t",self.tmuxname))

    def backup(self,remote=False):
        """
        remote: copy to the configured remote location after backup
        
        note: omits *.log
        """
        if remote:
            logger.error("Remote not implemented")
            return(self.ERROR_NOT_IMPLEMENTED)
        if len(self.backupdir)<1:
            logger.error("backup directory not set, see \"mcr mkconfig\"")
            return(self.ERROR_CONFIG)
        now = datetime.now()
        nows = "/backup_" + str(now.year) + str(now.month) + str(now.day)
        nows = nows + str(now.hour) + str(now.minute) + str(now.second) + "/"
        status = self.status()
        if status==0: # pre-notify and setup
            self.send("") # empty line
            self.send("broadcast [Backing up]")
            self.send("save-off")
            sleep(0.1) # needed?
            self.send("save-all")
        logger.debug("backing up to "+self.backupdir+nows)
        ret=0 # return status
        if not os.path.exists(self.backupdir):
            logger.error("backup directory does not exist")
            ret=self.ERROR_GENERAL
        else:
            try: copystatus = copytree(self.directory, self.backupdir+nows,
                    ignore=ignore_patterns('*.log'))
            except:
                logger.error("backup copy failed")
                ret=self.ERROR_GENERAL
        
        if status==0: # post-notify and cleanup - MUST BE RUN!
            self.send("") # empty line
            self.send("save-on")
            if not ret: self.send("broadcast [Backup complete]")
            else: self.send("broadcast [Backup failed, notify staff]")
        # TODO: remote
        return(ret)

    def kill(self): # TODO: make work w/ pid etc
        logger.warning("kill sometimes only kills the tmux session, not java!")
        return(subprocess.call(["tmux","kill-session","-t",self.tmuxname],
            stdout=open(os.devnull, 'w'),stderr=open(os.devnull, 'w')))

    def restart(self,wait=60,message=None,delay=60): # blocks until stopped!
        if self.status() == 0:
            if not message: message="Restarting server in "+delay+" seconds"
            if self.stop(wait=60,
                    message="Restarting server in "+delay+" seconds",
                    delay=delay) != 0:
                logger.error("couldn't stop server, restart failed")
                return(self.ERROR_GENERAL)
        else:
            logger.warning("server wasn't running, starting anyway")
        self.start()
        return(self.status())

    def send(self,data):
        if self.status():
            logger.error("server not running, can't send")
            return(self.ERROR_NOT_RUNNING)
        if type(data)!=type(str):
            data=" ".join(data)
        logger.debug("sending to",self.tmuxname,"data:",data)
        return(subprocess.call(["tmux","send-keys","-t",self.tmuxname+":0.0",data+" C-m"],
            stdout=open(os.devnull, 'w'),stderr=open(os.devnull, 'w')))

    def start(self):
        if self.status() == 0:
            logger.error("server already running")
            return(self.ERROR_GENERAL)
        # TODO: trap "" 2 20 ; exec javastuff
        command=self.javacmd+" -jar "+self.directory+"/"+self.jar
        logger.debug("starting: "+command)
        subprocess.call(
            ["tmux","new-session","-ds",self.tmuxname,"exec "+command],
            stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'),
            env={"HOME": os.path.expanduser("~"+self.user)}) # broken
        return(self.status())

    def status(self): # 0=running, 1=stopped
        return(subprocess.call(["tmux","has-session","-t",self.tmuxname],
            stdout=open(os.devnull, 'w'),stderr=open(os.devnull, 'w')))

    def stop(self,wait=30,message="Server stopping in 30 seconds...",delay=30):
        """
        wait: seconds to wait until the server is stopped before timing out
        message: message to send to users
        """
        self.send("") # newline
        if len(message)>0:
            self.send("broadcast "+message)
        time.sleep(delay)
        self.send("") # newline
        #self.send("timings merged")
        self.send("save-all")
        time.sleep(3)
        self.send("stop")
        for i in range(0,wait):
            if self.status() == 0:
                return(self.ERROR_NONE)
            time.sleep(1)
        return(self.ERROR_GENERAL)

    def update(self,plugin="all"):
        logger.critical("Not implemented")
        return(self.ERROR_NOT_IMPLEMENTED)


def getservers(user=""):
    """ Create a dictionary of all servers for a(=this) user """
    servers = {}
    for svname in os.listdir(os.path.expanduser("~"+user)+"/.config/mcr/"):
        servers[svname] = Server(svname,user)
    return servers

