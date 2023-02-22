#!/usr/bin/env python3

import argparse
import configparser
import dataclasses
from enum import Enum
import os
import re
import subprocess
import sys
from typing import Mapping


import psutil
import requests
from requests.auth import HTTPBasicAuth

@dataclasses.dataclass
class Cfg:
    stations: Mapping[str,str] = dataclasses.field(default_factory=dict)
    host: str = 'http://127.0.0.1'
    port: int = 9999
    password: str = ""

    @property
    def vlc_url(self):
        return f"{self.host}:{self.port}"

    @property   
    def basic_auth(self):
        return HTTPBasicAuth("", self.password)

class Commands(Enum):
    STOP = "pl_stop"
    PLAY = "pl_play"
    

def load_config():
    with open(os.path.expanduser("~/Library/Preferences/org.videolan.vlc/vlcrc")) as fdesc:
        raw = fdesc.read()
    passwords = re.findall(r'http-password=(.*)$', raw, re.MULTILINE)
    ports = re.findall(r'^http-port=(.*)$', raw, re.MULTILINE)
    
    cfg = Cfg()
    if len(passwords) == 1:
        cfg.password = passwords[0]
    
    if len(ports) == 1:
        cfg.port = ports[0]
    return cfg
        
    
def is_vlc_running(cfg):
    procs = [x for x  in psutil.process_iter(['pid', 'name']) if x.name().lower() == "vlc"]
    
    # We can probably end up in a situation with multiple instances running. Hopefully one will
    # respond to our http request
    return len(procs) >= 1

def launch_vlc(cfg):
    cmd = [
        'open', '-a', 'vlc'
    ]
    if not is_vlc_running(cfg):
        print("launching vlc")
        subprocess.run(cmd)
    else:
        print("vlc already running")

# http://127.0.0.1:9090/requests/status.xml?command=pl_stop
def vlc_status_cmd(cfg, cmd=None):
    if not cmd:
        cmd = "pl_stop"
    res = requests.get(f"{cfg.vlc_url}/requests/status.xml?command={cmd}", auth=cfg.basic_auth)
    #print(res)

if __name__ == "__main__":
    # TODO: Launch VLC
    cfg = load_config()
    
    cli_cmd = sys.argv[0]
    if cli_cmd.endswith("vlc_play"):
        vlc_status_cmd(cfg, Commands.PLAY.value)
    else:
        vlc_status_cmd(cfg)
        
        
    