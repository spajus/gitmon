#!/usr/bin/env python
# encoding: utf-8
"""
GitMon - the Git repository monitor and notifier

Created by Tomas Varaneckas on 2010-09-26.
Copyright (c) 2010 Tomas Varaneckas. All rights reserved.
"""

import os
import sys
import subprocess
from git import *

class Repository:
    """Works with GitPython's to produce nice status update information"""
    
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.path_full = os.path.expanduser(path)
        self.repo = Repo(self.path_full)
    
    def check_status(self):
        """Fetches remote heads and compares the received data to remote refs
         stored in local git repo. Differences are returned as a list of
         StatusUpdates """
        updates = []
        if verbose: 
            print 'Checking repo: %s' % self.name
        
        #get last commits in current remote ref
        local_commits = {}
        for rem in self.repo.remotes.origin.refs:
            local_commits[rem.remote_head] = rem.object
        
        try:
            #fetch new data
            if auto_pull:
                remote = self.repo.remotes.origin.pull()
            else:
                remote = self.repo.remotes.origin.fetch()
            #check latest commits from remote
            for fi in remote:
                branch = fi.ref.remote_head         
                try: #sometimes retrieval of remote commit fails
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
                                'NEW %s' % branch, remote_commit.author))
            return updates
        except AssertionError as e:
            if verbose:
                print 'Failed checking for updates: %s' % self.path

    def compare_commits(self, local, remote):
        """Compares local and remote commits to produce UpdateStatus
        if remote commit is newer"""
        if local.hexsha == remote.hexsha:
            return None
        if local.committed_date < remote.committed_date:
            return UpdateStatus(remote.message, author=remote.author)

class UpdateStatus:
    """Contains status update information which is displayed in user 
    notification"""
    
    def __init__(self, message, branch=None, author=None):
        self.author = author
        self.message = message
        self.branch = branch

class Gitmon:
    """Handles the big picture - config loading, checking for updates"""
    
    def __init__(self):
        self.config = {}
        self.repos = []
        self.conf_file = os.getenv('GITMON_CONF', '~/.gitmon.conf')
        self.conf_file = os.path.expanduser(self.conf_file)
        self.load_config()
        self.load_repos()
        if debug:
            print 'Loaded config: %s' % self.config
    
    def load_config(self):
        """Loads configuration into self.config dictionary"""
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
                    line = line.strip()
                    if not line.startswith('#') and line != '':
                        if not '=' in line:
                            print 'Warning: bad configuration line: %s' % line
                        else:
                            pair = line.strip().split('=', 1)
                            self.config[pair[0].strip()] = pair[1].strip()
            global notify_new_branch, auto_pull
            if self.config.has_key('notify.new.branch'):
                notify_new_branch = self.config['notify.new.branch']
            if self.config.has_key('auto.pull'):
                auto_pull = self.config['auto.pull']
                        
    def load_repos(self):
        """Loads repository definitions which are found in self.config"""
        for r in self.config.keys():
            if r.endswith('.path'):
                repo = r.replace('.path', '')
                if self.config.has_key('%s.name' % repo):
                    name = self.config['%s.name' % repo]
                else:
                    name = repo
                path = self.config['%s.path' % repo]
                if verbose: 
                    print 'Tracking repo: "%s" at %s' % (name, path)
                self.repos.append(Repository(name, path))    

            
    def check(self):
        """Checks the repositories and displays notifications"""
        for repo in self.repos:
            st = repo.check_status() 
            if st:
                mess = []
                for up in st:
                    mess.append('%s in %s:\n %s' % \
                                        (up.author, up.branch, up.message))
                self.notify(repo, '\n'.join(mess))
            
    def notify(self, repo, message):        
        """Notifies user about status updates with notification.command 
        from config. Replaces ${status} with update status message, 
        ${name} with repo name."""
        notif_cmd = self.config['notification.command'].split(' ')
        notif_cmd[notif_cmd.index('${status}')] = message
        notif_cmd[notif_cmd.index('${name}')] = '%s\n%s' % \
                                                    (repo.name, repo.path)
        proc = subprocess.Popen(notif_cmd, cwd=repo.path_full,
                                                stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        retcode = proc.wait()        
        if retcode != 0:
            print 'Error while notifying: %s, %s' % (retcode, args)
       
#Should gitmon produce verbose output? Override with -v when running.
verbose = False 
#Should gitmon notify when new branch is created? Set in config.
notify_new_branch = False   
#Should debug output be printed? Override with --debug when running.
debug = False    
#Current version. Print with --version when running
version = 0.1
#Should updates be pulled automatically?
auto_pull = False
        
def main():
    global verbose, debug
    program_name, args = sys.argv[0], sys.argv[1:]
    verbose = '-v' in args
    debug = '--debug' in args
    if '--version' in args:
        print 'GitMon v%s' % version
    if '-h' in args or '--help' in args:
        print 'Please read README file for help'
        sys.exit(0)
    app = Gitmon()
    app.check()

if __name__ == '__main__':
	main()
	