django-xinetd
=============

Script to deploy django using xinetd.

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
