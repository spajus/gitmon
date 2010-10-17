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

class Notifier(object):
    def notify(self, title=None, message=None, image=None):
        pass

    @classmethod
    def create(cls, type):
        if type == 'command.line':
            return CommandLineNotifier()

class CommandLineNotifier(Notifier):
    def notify(self, title, message, image):
        notif_cmd = self.config['notification.command'].split(' ')
        if '${message}' in notif_cmd:
            notif_cmd[notif_cmd.index('${message}')] = message.strip()
        if '${title}' in notif_cmd:
            notif_cmd[notif_cmd.index('${title}')] = '%s\n%s' % \
                                                    (repo.name, repo.path)
        if '${image}' in notif_cmd:
            notif_cmd[notif_cmd.index('${image}')] = gitmon_dir + '/git.png' 
        self.exec_notification(notif_cmd, repo.path_full)
       
    def exec_notification(self, notif_cmd, path):
        """Does the actual execution of notification command"""
        proc = subprocess.Popen(notif_cmd, cwd=path, stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        retcode = proc.wait()        
        if retcode != 0:
            print 'Error while notifying: %s, %s' % (retcode, args)
