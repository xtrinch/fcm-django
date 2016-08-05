#!/usr/bin/env python
import os.path
import push_notifications
from distutils.core import setup
import setuptools

VERSION = '0.1.1'

CLASSIFIERS = [
	"Development Status :: 5 - Production/Stable",
	"Environment :: Web Environment",
	"Framework :: Django",
	"Intended Audience :: Developers",
	"License :: OSI Approved :: MIT License",
	"Programming Language :: Python",
	"Programming Language :: Python :: 2.7",
	"Programming Language :: Python :: 3",
	"Programming Language :: Python :: 3.4",
	"Programming Language :: Python :: 3.5",
	"Topic :: Software Development :: Libraries :: Python Modules",
	"Topic :: System :: Networking",
]

setup(
	name="fcm-django",
	packages=[
		"push_notifications",
		"push_notifications/api",
		"push_notifications/migrations",
		"push_notifications/management",
		"push_notifications/management/commands",
	],
    install_requires=[
        'pyfcm==1.0.1',
        'Django'
    ],
	author=push_notifications.__author__,
	author_email=push_notifications.__email__,
	classifiers=CLASSIFIERS,
	description="Send push notifications to mobile devices through FCM in Django.",
	download_url="https://github.com/xtrinch/fcm-django/tarball/master",
	long_description='',
	url="https://github.com/xtrinch/fcm-django",
	version=push_notifications.__version__,
)
