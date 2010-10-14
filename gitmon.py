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
import time
from git import *

#Current version. Print with --version when running
version = "0.1.3"
#Should gitmon produce verbose output? Override with -v when running.
verbose = False 
#Should gitmon notify when new branch is created? Set in config.
notify_new_branch = False   
#Should debug output be printed? Override with --debug when running.
debug = False    
#Should updates be pulled automatically?
auto_pull = False
#How many latest commits to display?
max_new_commits = 5
#How many files to show in changeset. 0 means infinite.
max_files_info = 3


class Repository(object):
    """Works with GitPython's to produce nice status update information"""
    
    def __init__(self, name, path):
        """Initializes repository object with given name and path"""
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
        local_commits, remote_commits, local_refs = {}, [], []
        for rem in self.repo.remotes.origin.refs:
            local_refs.append(rem.name)
            local_commits[rem.remote_head] = rem.commit
        
        try:
            #fetch new data
            remote = self.repo.remotes.origin.fetch()
            #check latest commits from remote
            for fi in remote:
                if hasattr(fi.ref, 'remote_head'):
                    branch = fi.ref.remote_head       
                else:
                    if fi.ref.path.startswith('refs/tags/'):
                        if not fi.ref.path in local_refs:
                            up = BranchUpdates()
                            up.set_new_tag(fi.ref.commit, fi.ref.name)
                            updates.append(up)
                    else: 
                        print 'warning, unknown ref type: %s' % fi.ref
                        dump(fi.ref)
                    continue
                try: #http://byronimo.lighthouseapp.com/projects/51787-gitpython/tickets/44-remoteref-fails-when-there-is-character-in-the-name
                    remote_commit = fi.commit
                except Exception as e:
                    dump(e)
                    continue
                if local_commits.has_key(branch) or notify_new_branch:
                    if local_commits.has_key(branch):
                        local_commit = local_commits[branch]
                        new_branch = False
                    else:
                        local_commit = None
                        new_branch = True
                    ups = [update for update in self.get_updates(branch, local_commit, remote_commit)]
                    if ups or new_branch:
                        up = BranchUpdates(branch)
                        if new_branch:
                            up.set_new_branch(remote_commit)
                        if not remote_commit in remote_commits and not remote_commit in local_commits.values():
                            up.add(ups)
                            remote_commits.append(remote_commit)
                        updates.append(up)
                
            if auto_pull:
                try:
                    self.repo.remotes.origin.pull()
                except Exception as e:
                    if verbose:
                        print 'Failed pulling repo: %s, %s' % (self.name, e)
            return self.filter_updates(updates)
        except AssertionError as e:
            if verbose:
                print 'Failed checking for updates: %s' % self.path
                dump(e)

    def get_updates(self, branch, local, remote):
        """Retrieves updates from remote branch if series of remote commits are newer than local. Limits to max_new_commits."""
        depth = 0
        while depth < max_new_commits:
            depth += 1 
            if re.search('%s(~.*)?' % re.escape(branch), remote.name_rev) and self.is_remote_newer(local, remote):
                yield Update(remote)
            if remote.parents:
                remote = remote.parents[0]
            else:
                break

    def is_remote_newer(self, local, remote):
        """Compares local and remote updates and tells if remote is newer."""
        if local and local.hexsha == remote.hexsha:
            return False
        if not local or local.committed_date < remote.committed_date:
            return True

    def filter_updates(self, updates):
        """Filters updates to show only max_new_commits"""
        commits = {}
        for update in updates:
            for commit in update.updates:
                commits[commit] = update
        commits_by_date = sorted(commits.keys(), key=lambda commit: commit.date, reverse=True)[:max_new_commits]
        filtered_updates = []
        for commit in commits_by_date:
            update = commits[commit]
            if update in filtered_updates:
                update.updates.append(commit)
            else:
                update.updates = [commit]
                filtered_updates.append(update)
        return filtered_updates
            

class BranchUpdates(object):
    """A set of commits that happened in a branch"""
    def __init__(self, branch=None):
        """Initializes branch updates object"""
        self.branch = branch
        self.updates = []
        self.type = ''

    def set_new_branch(self, commit):
        """Marks this update status as new branch"""
        self.branch = self.branch
        self.type = ' (New branch)'
        self.updates.append(Update(commit, True))

    def set_new_tag(self, commit, tag):
        """Marks this update as new tag"""
        self.branch = tag
        self.type = ' (New tag)'
        self.updates.append(Update(commit, None, True))

    def add(self, update):
        """Appends an update to this update status"""
        self.updates.extend(update)

    def __str__(self):
        """Creates a string representation of all updates in the branch"""
        return '[%s]%s\n%s\n' % (self.branch, self.type, '\n'.join([str(sta) for sta in self.updates]))

class Update(object):
    """Contains information about single commit""" 
    def __init__(self, commit, new_branch=None, new_tag=False):
        self.files = []
        self.author = commit.committer.name.strip()
        self.date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(commit.committed_date))
        if new_branch:
            self.message = 'New branch created'
        else:
            self.message = commit.message.strip()
            if not new_tag:
                self.files = ['[%s+ %s-] %s' % \
                    (commit.stats.files[file]['insertions'], commit.stats.files[file]['deletions'], file) \
                        for file in commit.stats.files.keys()]

    def __str__(self):
        """Displays update representation. It's used in notification later."""
        mess = '----------\n%s\n%s: %s' % (self.date, self.author, self.message)
        if self.files:
            mess += '\nFiles:\n%s' % (len(self.files), '\n'.join(self.files[:max_files_info]))
            if len(self.files) > max_files_info:
                mess += '\n(%s more files)' % len(self.files) - max_files_info 
        return mess

class Gitmon(object):
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
            if self.config.has_key('max.new.commits'):
                max_new_commits = self.config['max.new.commits']
            if self.config.has_key('max.files.info'):
                max_files_info = self.config['max.files.info']
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
                    self.notify(repo, '\n'.join([str(sta) for sta in st]))
            
    def notify(self, repo, message):        
        """Notifies user about status updates with notification.command 
        from config. Replaces ${status} with update status message, 
        ${name} with repo name."""
        notif_cmd = self.config['notification.command'].split(' ')
        notif_cmd[notif_cmd.index('${status}')] = message.strip()
        notif_cmd[notif_cmd.index('${name}')] = '%s\n%s' % \
                                                    (repo.name, repo.path)
        self.exec_notification(notif_cmd, repo.path_full)
       
    def exec_notification(self, notif_cmd, path):
        """Does the actual execution of notification command"""
        proc = subprocess.Popen(notif_cmd, cwd=path, stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        retcode = proc.wait()        
        if retcode != 0:
            print 'Error while notifying: %s, %s' % (retcode, args)
    
        
def dump(obj):
    if debug:
        for attr in dir(obj):
            print 'obj.%s = %s' % (attr, getattr(obj, attr))
def main():
    global verbose, debug
    program_name, args = sys.argv[0], sys.argv[1:]
    verbose = '-v' in args
    debug = '--debug' in args
    if '--version' in args or '-v' in args:
        print 'GitMon v%s' % version
    if '-h' in args or '--help' in args:
        print 'Please read README file for help'
        sys.exit(0)
    app = Gitmon()
    app.check()

if __name__ == '__main__':
    main()
    
