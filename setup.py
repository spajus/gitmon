#!/usr/bin/env/ python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name = 'GitMon',
    version = '0.3.1',
    packages = find_packages('lib'),
    package_dir = {'' : 'lib'},
    scripts = ['misc/gitmon'],

    zip_safe = False,

    package_data = {'': ['*.png', '*.example']},
    requires = ('gitpython (>=0.2.9)', 'py_Growl_2_6 (>=0.0.7)'),
    install_requires = ['gitpython >= 0.2.9', 'py_Growl_2_6 >= 0.0.7'],

    #Metadata for PyPI
    url = 'http://github.com/spajus/gitmon/',
    author = 'Tomas Varaneckas',
    author_email = 'tomas.varaneckas@gmail.com',
    description = 'GitMon - The Git Repository Monitor',
    long_description = 'GitMon - The Git Repository Monitor',
    license = 'GPLv3',
    keywords = ['git', 'monitor', 'scm', 'repository']
)
