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
        self.name = name
        self.path = path
        self.path_full = os.path.expanduser(path)
        self.repo = Repo(self.path_full)
    def check_status(self):
        if verbose: 
            print 'Checking repo: %s' % self.name
        updates = []
        #get last commits in current remote ref
        local_commits = {}
        for rem in self.repo.remotes.origin.refs:
            local_commits[rem.remote_head] = rem.object
        try:
            #fetch new data
            remote = self.repo.remotes.origin.fetch()
            #check latest commits from remote
            for fi in remote:
                branch = fi.ref.remote_head
                #if fi.flags & fi.NEW_TAG:
                #    continue                
                try:
                    remote_commit = fi.commit
                except Exception:
                    continue
                if local_commits.has_key(branch):
                    local_commit = local_commits[fi.ref.remote_head]
                    up = self.compare_commits(local_commit, remote_commit)
                    if up:
                        up.branch = branch
                        updates.append(up)
                else:
                    if notify_new_branch:
                        updates.append(
                            UpdateStatus(remote_commit.message, 
                                'NEW %s' % branch))
            return updates
        except AssertionError as e:
            print 'Failed checking for updates: %s' % self.path

    def compare_commits(self, local, remote):
        if local.hexsha == remote.hexsha:
            return None
        if local.committed_date < remote.committed_date:
            return UpdateStatus(remote.message)

class UpdateStatus:
    def __init__(self, message, branch=None):
        self.message = message
        self.branch = branch

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
            if verbose:
                print 'Loading configuration from %s' % self.conf_file
            with open(self.conf_file) as conf:
                for line in conf:
                    if not line.strip().startswith('#') and line.strip() != '':
                        if not '=' in line:
                            print 'Warning: bad configuration line: %s' % line
                        else:
                            pair = line.strip().split('=', 1)
                            self.config[pair[0].strip()] = pair[1].strip()
            if self.config.has_key('notify.new.branch'):
                global notify_new_branch
                notify_new_branch = self.config['notify.new.branch']
                        
    def load_repos(self):
        for r in self.config['monitor'].split(','):
            r = r.strip()
            name = self.config[r + '.name']
            path = self.config[r + '.path']
            if verbose: 
                print 'Tracking repo: "%s" at %s' % (name, path)
            self.repos.append(Repository(name, path))    
    
    def __init__(self):
        self.config = {}
        self.repos = []
        self.conf_file = os.getenv('GITMON_CONF', '~/.gitmon.conf')
        self.conf_file = os.path.expanduser(self.conf_file)
        self.load_config()
        self.load_repos()
        if debug:
            print 'Loaded config: %s' % self.config     
            
    def check(self):
        for repo in self.repos:
            st = repo.check_status() 
            if st:
                mess = []
                for up in st:
                    mess.append('In %s: %s' % (up.branch, up.message))
                self.notify(repo, '\n'.join(mess))
            
    def notify(self, repo, message):
          notif_cmd = self.config['notification.command'].split(' ')
          notif_cmd[notif_cmd.index('${status}')] = message
          notif_cmd[notif_cmd.index('${name}')] = '%s\n%s' % (repo.name, repo.path)
          proc = subprocess.Popen(notif_cmd, cwd=repo.path_full, stdout=subprocess.PIPE)
          output, _ = proc.communicate()
          retcode = proc.wait()        
          if retcode != 0:
              print 'Error while notifying: %s, %s' % (retcode, args)
          print output
        
verbose = False 
notify_new_branch = False   
debug = False    
        
def main():
    global verbose
    global debug
    program_name, args = sys.argv[0], sys.argv[1:]
    verbose = '-v' in args
    debug = '--debug' in args
    if '-h' in args or '--help' in args:
        print 'Please read README file for help'
        sys.exit(0)
    app = Gitmon()
    app.check()

if __name__ == '__main__':
	main()

