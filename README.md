GitMon - The Git Repository Monitor
===================================

Installation
------------

Requirements:

* Python 2.6+
* Git
* growlnotify (http://growl.info/), python-notify (for libnotify on linux) or a command line tool for notifications

To install without downloading source:

    sudo easy_install gitmon

or from source folder:

    sudo python setup.py install

When building from source, you may need to install gitpython (sudo easy_install gitpython).

Usage
-----

    usage: gitmon [-v] [--version] [-c <path>] [-h|--help]

    Parameters:
      -v          Verbose output
      --version   Prints GitMon version
      -c <path>   Runs GitMon using configuration file provided in <path>
      -h, --help  Prints help

    Commands:
                  When no command is given, GitMon scans repositories for updates
      test        Checks configuration and displays test notification
      configure   Opens GitMon configuration file for editing

You have three options for placing your configuration file:

1. Recommended approach: Run 'gitmon' after a fresh install and it will create you ~/.gitmon.conf, then run 'gitmon configure' to edit it
2. Put gitmon.conf anywhere you want and define GITMON_CONF env variable ('gitmon configure' will not work though)
3. Run gitmon with -c /path/to/config.file (useful during development)

Known Issues
------------

* When there is a large number of changes, growl notification may exceed desktop height therefore it gets not fully visible.

Roadmap
-------

* GUI version (at least for Mac OS X)

Contact
-------

Suggestions, improvements?
tomas.varaneckas@gmail.com

