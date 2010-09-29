#!/usr/bin/env python
# encoding: utf-8
"""
gitmon.py

Created by Tomas Varaneckas on 2010-09-26.
Copyright (c) 2010 Tomas Varaneckas. All rights reserved.
"""
import os

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
            print 'loading configuration from %s' % self.conf_file
            with open(self.conf_file) as conf:
                for line in conf:
                    if not line.strip().startswith('#') and line.strip() != '':
                        if not '=' in line:
                            print 'Warning: bad configuration line: %s' % line
                        else:
                            pair = line.strip().split('=', 1)
                            self.config[pair[0].strip()] = pair[1].strip()
                        
    
    def __init__(self):
        self.config = {}
        self.conf_file = os.getenv('GITMON_CONF', '~/.gitmon.conf')
        self.conf_file = os.path.expanduser(self.conf_file)
        self.load_config()
        print 'loaded config: %s' % self.config
        
        
        
def main():
    app = Gitmon()

if __name__ == '__main__':
	main()

