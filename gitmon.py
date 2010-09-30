#!/usr/bin/env python
# encoding: utf-8
"""
gitmon.py

Created by Tomas Varaneckas on 2010-09-26.
Copyright (c) 2010 Tomas Varaneckas. All rights reserved.
"""
import os
import sys
import subprocess
from git import *

class Repository:
    def __init__(self, name, path):
        self.repo = Repo(path)
        self.name = name
        self.path = path
        self.path_full = os.path.expanduser(path)
    def check_status(self):
        if verbose: 
            print 'Checking repo: %s' % self.name
        info = self.repo.remotes.origin.fetch()
        return "%s:\nAvailable updates: %s" % (self.path, len(info))

class Gitmon:
    
    def load_config(self):
        """loads configuration into self.config"""
        config_found = os.path.isfile(self.conf_file)
        if not config_found:
            print 'creating initial configuration in %s' % self.conf_file 
            config = open(self.conf_file, 'w')
            config.write('test')
            config.close()
        else:
            print 'Loading configuration from %s' % self.conf_file
            with open(self.conf_file) as conf:
                for line in conf:
                    if not line.strip().startswith('#') and line.strip() != '':
                        if not '=' in line:
                            print 'Warning: bad configuration line: %s' % line
                        else:
                            pair = line.strip().split('=', 1)
                            self.config[pair[0].strip()] = pair[1].strip()
                        
    def load_repos(self):
        for r in self.config['monitor'].split(','):
            r = r.strip()
            name = self.config[r + '.name']
            path = self.config[r + '.path']
            print 'Tracking repo: "%s" at %s' % (name, path)
            self.repos.append(Repository(name, path))    
    
    def __init__(self):
        self.config = {}
        self.repos = []
        self.conf_file = os.getenv('GITMON_CONF', '~/.gitmon.conf')
        self.conf_file = os.path.expanduser(self.conf_file)
        self.load_config()
        self.load_repos()
        if verbose:
            print 'Loaded config: %s' % self.config     
            
    def check(self):
        for repo in self.repos:
            st = repo.check_status() 
            self.notify(repo, st)
            
    def notify(self, repo, message):
          notif_cmd = self.config['notification.command'].split(' ')
          notif_cmd[notif_cmd.index('${status}')] = message
          notif_cmd[notif_cmd.index('${name}')] = repo.name
          proc = subprocess.Popen(notif_cmd, cwd=repo.path_full, stdout=subprocess.PIPE)
          output, _ = proc.communicate()
          retcode = proc.wait()        
          if retcode != 0:
              print 'Error while notifying: %s, %s' % (retcode, args)
          print output
        
verbose = False        
        
def main():
    global verbose
    program_name, args = sys.argv[0], sys.argv[1:]
    verbose = '-v' in args
    app = Gitmon()
    app.check()

if __name__ == '__main__':
	main()

