GitMon - The Git Repository Monitor
===================================

Installation
------------

Requirements:

* Python 2.6+
* Git
* GitPython (easy_install gitpython)
* growlnotify (http://growl.info/), libnotify-bin (on linux) or any other notification tool
* crontab or other scheduling tool (optional)

Usage
-----

    gitmon [-v] [--debug] [-c gitmon.conf]

You have three  options for placing your configuration file:

1. Create ~/.gitmon.conf 
2. Put gitmon.conf anywhere you want and define GITMON_CONF env variable
3. Run gitmon with -c /path/to/config.file

Refer to provided gitmon.conf.example when creating your configuration.

You can set up a crontab with your prefered timing to execute gitmon 
automatically, i.e: 

    */5 * * * * /path/to/gitmon > /tmp/gitmon.log

Note: 'git' and 'python' commands should be in crontab's PATH

If you've done everything right, you should get some notifications.

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

