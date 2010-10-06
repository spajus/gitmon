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
import re    
from git import *

#Current version. Print with --version when running
version = 0.1
#Should gitmon produce verbose output? Override with -v when running.
verbose = False 
#Should gitmon notify when new branch is created? Set in config.
notify_new_branch = False   
#Should debug output be printed? Override with --debug when running.
debug = False    
#Should updates be pulled automatically?
auto_pull = False
#How many latest commits to display?
max_last_commits = 5

def dump(obj):
    for attr in dir(obj):
        print "obj.%s = %s" % (attr, getattr(obj, attr))

class Repository:
    """Works with GitPython's to produce nice status update information"""
    
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.path_full = os.path.expanduser(path)
        try:
            self.repo = Repo(self.path_full)
        except Exception as e:
            print 'Could not load repository at path: %s: %s' % (self.path_full, e)
    
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
            local_commits[rem.remote_head] = rem.commit
        
        try:
            #fetch new data
            remote = self.repo.remotes.origin.fetch()
            #check latest commits from remote
            for fi in remote:
                if hasattr(fi.ref, 'remote_head'):
                    branch = fi.ref.remote_head       
                else:
                    #this is probably a tag, let's skip it for now
                    continue
                try: #sometimes reference may not exist
                    remote_commit = fi.commit
                except Exception as e:
                    print 'Could not fetch %s (%s): %s' % (self.name, branch, e)
                    continue
                if local_commits.has_key(branch) or notify_new_branch:
                    if local_commits.has_key(branch):
                        local_commit = local_commits[branch]
                    else:
                        local_commit = None
                    ups = self.compare_commits(branch, local_commit, remote_commit)
                    if ups:
                        up = UpdateStatus(branch)
                        up.add(ups)
                        updates.append(up)
            if auto_pull:
                try:
                    self.repo.remotes.origin.pull()
                except Exception as e:
                    if verbose:
                        print 'Failed pulling repo: %s, %s' % (self.name, e)
            return updates
        except AssertionError as e:
            if verbose:
                print 'Failed checking for updates: %s' % self.path
                dump(e)

    def compare_commits(self, branch, local, remote, depth=1, updates=None):
        """Compares local and remote commits to produce list of Update
        if remote commit is newer"""
        if local and local.hexsha == remote.hexsha:
            return updates
        if not local or local.committed_date < remote.committed_date:
            if not updates:
                updates = []
            updates.append(Update(remote))
            if remote.parents and depth <= max_last_commits:
                self.compare_commits(local, remote.parents[0], depth + 1, updates)
            return updates

class UpdateStatus:
    """Contains status update information which is displayed in user 
    notification"""
    
    def __init__(self, branch=None):
        self.branch = branch
        self.updates = []

    def add(self, update):
        self.updates.extend(update)

    def __str__(self):
        mess = []
        for up in self.updates:
            mess.append('%s' % up)
        return 'In %s:\n%s' % (self.branch, '\n'.join(mess))

class Update:
    
    def __init__(self, commit):
        self.message = commit.message
        self.author = commit.committer.name
        self.stats = commit.stats.total

    def __str__(self):
       return '%s: %s (-:%s +:%s f:%s)' % (self.author, self.message, self.stats.deletions, self.stats.insertions, self.stats.files)

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
        if '-c' in sys.argv:
            self.conf_file = sys.argv[sys.argv.index('-c') + 1]
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
        for key, val in self.config.items():
            params = re.search("\$\{(.+)\}", val)
            if params:
                for par in params.groups():
                    if self.config.has_key(par):
                        self.config[key] = re.sub("\$\{(.+)\}", self.config[par], val)
                        
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
            if hasattr(repo, 'repo'):
                st = repo.check_status() 
                if st:
                    mess = []
                    for status in st:
                        mess.append('%s' % status)
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
    
