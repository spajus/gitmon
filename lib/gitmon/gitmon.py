"""
GitMon - The Git Repository Monitor
Copyright (C) 2010  Tomas Varaneckas
http://www.varaneckas.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os
import re
import time
import shutil
from git import *
from notifiers import *

#Should gitmon produce verbose output? Override with -v when running.
verbose = False
#Should debug output be printed? Override with --debug when running.
debug = False
#Should gitmon notify when new branch is created? Set in config.
notify_new_branch = 1
#Should gitmon notify when new tag is created? Set in config
notify_new_tag = 1
#Should updates be pulled automatically?
auto_pull = 0
#Should stale remote references be deleted and notified about?
auto_delete_stale = 0
#How many latest commits to display?
max_new_commits = 5
#How many files to show in changeset. 0 means infinite.
max_files_info = 3
#How deep to scan for repos by default
default_scan_depth = 3
#Program dir
gitmon_dir = '.'
#Notifier type
notifier_type = 'command.line'
#Repository check delay in minutes
check_delay = 5
#use built-in scheduler
scheduler_builtin = 0

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
         StatusUpdates

         FIXME: in future removal of tags and branches must also be displayed.
         Local refs: repo.remotes.origin.refs
         Remote refs:
         fi = repo.remotes.origin.fetch()
         check if fi[x].ref is not in local refs and notify. Perhaps delete
         local ref to avoid notification reappearance.

         """
        updates = []
        if verbose:
            print u'Checking repo: %s' % self.name

        #get last commits in current remote ref
        local_commits, remote_commits, local_refs, remote_refs = {}, [], [], []
        for rem in self.repo.remotes.origin.refs:
            try:
                local_refs.append(rem.name)
                local_commits[rem.remote_head] = rem.commit
            except Exception as e:
                if verbose:
                    print u'Failed getting remote branch %s on repo %s: %s' % (rem.name,
                                                                 self.name, e)
        try:
            #fetch new data
            remote = self.repo.remotes.origin.fetch()
            #check latest commits from remote
            for fi in remote:
                remote_refs.append(fi.ref)
                if hasattr(fi.ref, 'remote_head'):
                    branch = fi.ref.remote_head
                else:
                    if notify_new_tag and fi.ref.path.startswith('refs/tags/'):
                        if not fi.ref.path in local_refs:
                            up = BranchUpdates()
                            up.set_new_tag(fi.ref.commit, fi.ref.name)
                            updates.append(up)
                    else:
                        print u'warning, unknown ref type: %s' % fi.ref
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
                        print u'Failed pulling repo: %s, %s' % (self.name, e)
            # At this point we're done with checking for new additions, now let's check
            # if anything was removed

            # It's possible to simply use self.repo.stale_refs for that, but it makes
            # a remote call
            if auto_delete_stale:
                try:
                    for ref in self.repo.remotes.origin.stale_refs:
                        if hasattr(ref, 'remote_head'):
                            if ref.remote_head == 'HEAD':
                                continue
                            name = ref.remote_head
                        else:
                            name = ref.name
                        up = BranchUpdates(name)
                        # XXX old commits may get lost within many updates even if branch/tag was just removed
                        up.set_removed(ref.commit)
                        updates.append(up)
                        RemoteReference.delete(self.repo, ref)
                except Exception as e:
                    if verbose:
                        print u'Failed cleaning up stale refs in repo: %s, %s' % (self.name, e)
            updates = self.filter_updates(updates)
            return updates
        except AssertionError as e:
            if verbose:
                print u'Failed checking for updates: %s' % self.path
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
        self.updates.append(Update(commit, new_branch=True))

    def set_new_tag(self, commit, tag):
        """Marks this update as new tag"""
        self.branch = tag
        self.type = ' (New tag)'
        self.updates.append(Update(commit, new_tag=True))

    def set_removed(self, commit):
        """Marks this update as deleted in remote origin"""
        self.type = ' (Removed)'
        self.updates.append(Update(commit, deleted=True))

    def add(self, update):
        """Appends an update to this update status"""
        self.updates.extend(update)

    def __str__(self):
        """Creates a string representation of all updates in the branch"""
        return u'[%s]%s\n%s\n' % (self.branch, self.type, u'\n'.join([unicode(sta) for sta in self.updates]))

class Update(object):
    """Contains information about single commit"""
    def __init__(self, commit, new_branch=False, new_tag=False, deleted=False):
        self.files = []
        if new_branch or new_tag or deleted:
            self.date = time.strftime('%Y-%m-%d %H:%M:%S')
            self.author = ''
        else:
            self.author = commit.committer.name.strip()

        self.date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(commit.committed_date))
        if new_branch:
            self.message = 'New branch created'
        elif deleted:
            self.message = 'This remote reference no longer appears in origin. It was removed locally.'
        else:
            self.message = commit.message.strip()
            if not new_tag:
                self.files = ['[%s+ %s-] %s' % \
                    (commit.stats.files[file]['insertions'], commit.stats.files[file]['deletions'], file) \
                        for file in commit.stats.files.keys()]

    def __str__(self):
        """Displays update representation. It's used in notification later."""
        if self.author:
            mess = '----------\n%s\n%s: %s' % (self.date, self.author, self.message)
        else:
            mess = '----------\n%s\n%s' % (self.date, self.message)
        if self.files:
            if max_files_info > 0:
                mess += '\nFiles:\n%s' % '\n'.join(self.files[:max_files_info])
                if len(self.files) > max_files_info:
                    more_files = len(self.files) - max_files_info
                    mess += '\n(%s more %s)' % (more_files, pluralize('file', more_files))
            else:
                mess += '\nFiles:\n%s' % '\n'.join(self.files)
        return mess

class Gitmon(object):
    """Handles the big picture - config loading, checking for updates"""

    def __init__(self, conf_file = None, g_verbose = False, g_debug = False):

        global verbose, debug
        verbose, debug = g_verbose, g_debug

        self.config = {}
        self.repos = []
        self.scan_dirs = []
        self.conf_file = os.getenv('GITMON_CONF', '~/.gitmon.conf')
        self.conf_file = os.path.expanduser(self.conf_file)
        if conf_file:
            self.conf_file = os.path.expanduser(conf_file)
        self.load_config()
        self.load_repos()
        self.scan_repos()
        self.check_config()
        if debug:
            print 'Loaded config: %s' % self.config

    def load_config(self):
        """Loads configuration into self.config dictionary"""
        global gitmon_dir
        gitmon_dir = os.path.dirname(__file__)
        config_found = os.path.isfile(self.conf_file)
        if not config_found:
            shutil.copyfile(gitmon_dir + '/gitmon.conf.example', os.path.expanduser('~/.gitmon.conf'))
            print """Configuration not found! ~/.gitmon.conf was created for you. \
Edit it to tailor your needs.

You can schedule gitmon to run with contab:

# Edit with 'crontab -e'
# 'git' must be in cron's PATH
PATH=/usr/bin:/usr/local/bin/:/bin
*/5 * * * * gitmon
"""
            sys.exit(0)
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
        for key, val in self.config.items():
            params = re.search("\$\{(.+)\}", val)
            if params:
                for par in params.groups():
                    if self.config.has_key(par):
                        self.config[key] = re.sub("\$\{(.+)\}", self.config[par], val)
        self.set_globals()

    def check_config(self):
        if not self.repos:
            print 'Your configuration file has no repositories. Make sure you have defined \
repositories or scanned roots in your configuration. Refer to gitmon.conf.example for details.'
            sys.exit(-1)
        else:
            if verbose:
                print 'Configuration OK, tracking %s repositories' % len(self.repos)

    def set_globals(self):
        """Sets global parameters from configuration"""
        global notify_new_branch, notify_new_tag, auto_pull, max_new_commits, max_files_info
        global notifier_type, auto_delete_stale, check_delay, scheduler_builtin
        if self.config.has_key('notify.new.branch'):
            notify_new_branch = int(self.config['notify.new.branch'])
        if self.config.has_key('notify.new.tag'):
            notify_new_tag = int(self.config['notify.new.tag'])
        if self.config.has_key('auto.pull'):
            auto_pull = int(self.config['auto.pull'])
        if self.config.has_key('max.new.commits'):
            max_new_commits = int(self.config['max.new.commits'])
        if self.config.has_key('max.files.info'):
            max_files_info = int(self.config['max.files.info'])
        if self.config.has_key('notifier.type'):
            notifier_type = self.config['notifier.type']
        if self.config.has_key('auto.delete.stale'):
            auto_delete_stale = int(self.config['auto.delete.stale'])
        if self.config.has_key('check.delay.minutes'):
            check_delay = int(self.config['check.delay.minutes'])
        if self.config.has_key('scheduler.builtin'):
            scheduler_builtin = bool(int(self.config['scheduler.builtin']))

    def use_builtin_scheduler(self):
        return scheduler_builtin

    def load_repos(self):
        """Loads repository definitions which are found in self.config"""
        for r in self.config.keys():
            if r.startswith('repo.') and r.endswith('.path'):
                repo = r.replace('.path', '')
                if self.config.has_key('%s.name' % repo):
                    name = self.config['%s.name' % repo]
                else:
                    name = repo.replace('repo.', '')
                path = self.config['%s.path' % repo]
                if verbose:
                    print 'Tracking repo: "%s" at %s' % (name, path)
                self.repos.append(Repository(name, path))

    def scan_repos(self):
        """Scans provided dirs and recursively searches for repositories"""
        for root in self.config.keys():
            if root.startswith('scan.') and root.endswith('.path'):
                root = root.replace('.path', '')
                if self.config.has_key('%s.name' % root):
                    name = self.config['%s.name' % root]
                else:
                    name = root.replace('scan.', '')
                if self.config.has_key('%s.depth' % root):
                    depth = int(self.config['%s.depth' % root])
                else:
                    depth = default_scan_depth
                dir = os.path.expanduser(self.config['%s.path' % root])
                if verbose:
                    print 'Scanning for repos in: %s' % dir
                for repo in self.scan_dir_for_repos(dir, name, depth):
                    self.repos.append(repo)

    def scan_dir_for_repos(self, root, root_name, depth):
        """Scans directory recursively in serch of git repositories"""
        if not depth:
            return
        for f in os.listdir(root):
            dir = '%s/%s' % (root, f)
            if os.path.isdir(dir):
                if self.is_git_repo(dir):
                    if verbose:
                        print 'Found git repo: %s' % dir
                    yield Repository('%s (%s)' % (f, root_name), dir)
                else:
                    for repo in self.scan_dir_for_repos(dir, root_name, depth - 1):
                        yield repo

    def is_git_repo(self, dir):
        return '.git' in os.listdir(dir) and os.path.isdir(dir + '/.git')

    def check(self):
        """Checks the repositories and displays notifications"""
        for repo, st in self.get_repo_updates():
            if st:
                self.notify(repo, u'\n'.join([unicode(sta) for sta in st]))

    def get_repo_updates(self):
        for repo in self.repos:
            try:
                if hasattr(repo, 'repo'):
                    yield (repo, repo.check_status())
            except Exception as e:
                if verbose:
                    print 'Failed checking updates for %s: %s' % (repo.name, e)

    def notify(self, repo, message):
        """Notifies user about status updates using given notifier.type
        from config. Replaces ${message} with update status message,
        ${title} with repo name and ${image} with path to git.png."""
        title = '%s\n%s' % (repo.name, repo.path.replace(os.path.expanduser('~'), '~'))
        message = message.strip()
        image = gitmon_dir + '/git.png'
        notifier = Notifier.create(notifier_type, self.config)
        if verbose:
            print 'Using notifier: %s' % notifier_type
            print 'Using notification icon: %s' % image
        notifier.notify(title, message, image, repo.path_full)

    def selftest(self):
        print "GitMon Self Test. You should see a notification right now. Install Growl from http://growl.info if you don't."
        notifier = Notifier.create(notifier_type, self.config)
        notifier.notify('GitMon Test', 'It Works!', gitmon_dir + '/git.png', gitmon_dir)

def dump(obj):
    if debug:
        for attr in dir(obj):
            print 'obj.%s = %s' % (attr, getattr(obj, attr))
def pluralize(word, count):
    if count > 1:
        return '%ss' % word
    return word



