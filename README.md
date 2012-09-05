django-xinetd
=============

Script to deploy django using xinetd.

# System requirements #

1. Linux (Script was tested with Ubuntu 12.04)
1. Python (Script was tested with 2.7 version)
1. xinetd
1. Django (Script was tested with 1.4 version)

If xinetd is not installed:

`apt-get install xinetd`

# Installation #

## Script installation ##

1. Copy django_xinetd.py file where you want to.
1. Open script in your favorite text editor.
1. Set hashbang string to your python path. If you use distrutive's 
   python it can be '/usr/bin/python'.
1. Set DOCUMENT_ROOT variable to your document root.
1. Set STATIC_FILES variable.
1. Set PROJECT_PATH variable.
1. Set DJANGO\_SETTINGS\_MODULE variable.




# xinetd configuration #

A configuration process is described for Ubuntu (It has to be the same
for Debian).

## xinetd installation ##

`apt-get install xinetd`

## /etc/xinetd/django_xinetd file ##

Create /etc/xinetd.d/django_xinetd file:

    `service django_xinetd
    {
    	disable		= no
    	socket_type	= stream
    	user		= root
    	wait		= no
    	port		= 9002
    	protocol	= tcp
    	server		= /path/to/script/django_xinetd.py
    #	log_type 	= FILE /var/log/servicelog
    #	log_on_success	= PID
    #	log_on_failure	= HOST
    }
	`

## /etc/services file ##

Add line to /etc/services file:

`django_xinetd	9002/tcp`

## Restart xinetd ##

`/etc/init.d/xinetd restart`
