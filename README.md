django-xinetd
=============

# Info #

Author: Evgeny Kazanov

# Introduction #

Script to deploy django using xinetd. It allows to use Django at
localhost without webserver. The main goal is to use Django for local
web applications and do not spend time and computer resources when
these applications are not working.

# Why yet another deployment way? #

I want to use Django for local applications. It has pretty much all
features for it. Django can work without DB server, using SQLite. The
week place is websever. You can use separate webserver (Apache) or
devserver which is part of Django. Sometimes you have not got
webserver on computer. You can use devserver. But you need start a
separate process at startup for each of your applications in such
case. It takes time. It wastes resources.

'django-xinetd' works using xinetd. xinetd listens a port. If it gets
a request, it starts django-xinetd script and passes the request to STDIN.
So when you do not need your applications they are not started.

# System requirements #

1. Linux (Script was tested with Ubuntu 12.04)
1. Python (Script was tested with 2.7 version)
1. xinetd
1. Django (Script was tested with 1.4 version)

If xinetd is not installed, install it. This is Debian/Ubuntu command:

`apt-get install xinetd`

# Installation #

## Script installation ##

1. Copy django_xinetd.py file where you want to. Your project directory is a reasonably good place for it.
1. Open script in your favorite text editor.
1. Set shabang string to your python path. If you use your system 
   python it can be '/usr/bin/python'.
1. Set DOCUMENT_ROOT variable to your document root.
1. Set STATIC_FILES variable.
1. Set PROJECT_PATH variable.
1. Set LOGGING_NAME variable.
1. Set DJANGO\_SETTINGS\_MODULE variable.

# xinetd configuration #

A configuration process is described for Ubuntu (It has to be the same
for Debian). The 9002 port is used.

## /etc/xinetd/django_xinetd file ##

Create /etc/xinetd.d/django_xinetd file:

    `service django_xinetd
    {
    	disable		= no
    	socket_type	= stream
    	user		= <your user name>
    	wait		= no
    	port		= 9002
    	protocol	= tcp
    	server		= /path/to/script/django_xinetd.py
    }

## /etc/services file ##

Add line to /etc/services file:

`django_xinetd	9002/tcp`

## Restart xinetd ##

`/etc/init.d/xinetd restart`

# Usage #

Open http://localhost:9002 in your browser.


