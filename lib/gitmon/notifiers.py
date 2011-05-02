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

import subprocess
import Growl

class Notifier(object):

    def __init__(self, config):
        self.config = config

    def notify(self, title=None, message=None, image=None, cwd=None):
        pass

    @classmethod
    def create(cls, type, config):
        """Returns singleton instance of given notifier type"""
        if type == 'command.line':
            return CommandLineNotifier.instance(config)
        if type == 'growl':
            return GrowlNotifier.instance(config)

class CommandLineNotifier(Notifier):

    inst = None

    @classmethod
    def instance(cls, config):
        if not CommandLineNotifier.inst:
            CommandLineNotifier.inst = CommandLineNotifier(config)
        return CommandLineNotifier.inst

    def notify(self, title, message, image, cwd):
        notif_cmd = self.config['command.line.cmd'].split(' ')
        if '${message}' in notif_cmd:
            notif_cmd[notif_cmd.index('${message}')] = message
        if '${title}' in notif_cmd:
            notif_cmd[notif_cmd.index('${title}')] = title
        if '${image}' in notif_cmd:
            notif_cmd[notif_cmd.index('${image}')] = image
        self.exec_notification(notif_cmd, cwd)

    def exec_notification(self, notif_cmd, path):
        """Does the actual execution of notification command"""
        proc = subprocess.Popen(notif_cmd, cwd=path, stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        retcode = proc.wait()
        if retcode != 0:
            print 'Error while notifying: %s, %s' % (retcode, args)

class GrowlNotifier(Notifier):

    inst = None

    @classmethod
    def instance(cls, config):
        if not GrowlNotifier.inst:
            GrowlNotifier.inst = GrowlNotifier(config)
        return GrowlNotifier.inst

    def notify(self, title, message, image, cwd):
        if image:
            image = Growl.Image.imageFromPath(image)
        sticky = bool(int(self.config['growl.sticky.notifications']))
        growl = Growl.GrowlNotifier(applicationName='GitMon', \
                applicationIcon=image, \
                notifications=['update'], \
                defaultNotifications=['update'])
        if not hasattr(self, 'registered'):
            growl.register()
            self.registered = True
        growl.notify('update', title, message, icon=image, sticky=sticky)

