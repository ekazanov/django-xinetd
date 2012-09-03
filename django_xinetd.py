#!/home/evgeny/projects/079-django-tmpl-bin/www/env/bin/python
"""
Script to deploy Django using xinetd.
"""
import os, sys, re
import mimetypes
from StringIO import StringIO
import django.core.handlers.wsgi
from django.utils import importlib

DOCUMENT_ROOT = "/home/evgeny/projects/079-django-tmpl-bin/www/insert_your_project_name_here/static/documentroot"
STATIC_FILES = ["/favicon.ico","/robots.txt"]
PROJECT_PATH = "/home/evgeny/projects/079-django-tmpl-bin/www/insert_your_project_name_here"
DJANGO_SETTINGS_MODULE = "insert_your_project_name_here.settings"

sys.path.append(PROJECT_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

settings = importlib.import_module(os.environ["DJANGO_SETTINGS_MODULE"])

def get_request():
    request = ""
    request_body = ""
    while True:
        # GET headers
        request += sys.stdin.readline()
        if request.endswith("\r\n\r\n") or request.endswith("\n\n"):
            break
    # Get content length
    if request.find("POST") != -1:
        headers = request.split("\r\n")
        for h in headers[1:]:
            if h == "":
                continue
            k,v = h.split(": ")
            if k == "Content-Length":
                content_length = int(v)
        request_body += sys.stdin.read(content_length)
    return (request,request_body)

request_text,request_body = get_request()

# Parse request
request_dict = {}
request_arr = request_text.split('\r\n')
request_dict["REQUEST_METHOD"],request_dict["PATH_INFO"],request_dict["SERVER_PROTOCOL"] = request_arr[0].split(" ")
for l in request_arr[1:]:
    if len(l) == 0:
        continue
    k,v = l.split(": ")
    request_dict[k] = v
if request_dict.has_key('Host'):
    request_dict["SERVER_NAME"],request_dict["SERVER_PORT"] = request_dict["Host"].split(":")
if re.findall('\?',request_dict["PATH_INFO"]):
    request_dict["PATH"],request_dict["QUERY_STRING"] = request_dict["PATH_INFO"].split('?')

def set_env_var_from_header(env_var_name,header_name,headers_dict):
    if headers_dict.has_key(header_name):
        os.environ[env_var_name] = headers_dict[header_name]
    return

set_env_var_from_header("REQUEST_METHOD","REQUEST_METHOD",request_dict)
set_env_var_from_header("SERVER_NAME","SERVER_NAME",request_dict)
set_env_var_from_header("SERVER_PORT","SERVER_PORT",request_dict)
set_env_var_from_header("PATH_INFO","PATH_INFO",request_dict)
set_env_var_from_header("SERVER_PROTOCOL","SERVER_PROTOCOL",request_dict)
set_env_var_from_header("QUERY_STRING","QUERY_STRING",request_dict)
set_env_var_from_header("HTTP_COOKIE","Cookie",request_dict)
set_env_var_from_header("CONTENT_LENGTH","Content-Length",request_dict)
set_env_var_from_header("CONTENT_TYPE","Content-Type",request_dict)

# Process static files
is_static = False
for static_file in STATIC_FILES:
    if request_dict["PATH_INFO"] == static_file:
        is_static = True
        file_name = request_dict["PATH_INFO"].lstrip("/")
        file_path = os.path.join(DOCUMENT_ROOT,file_name)
        break
if request_dict["PATH_INFO"].startswith(settings.STATIC_URL):
    is_static = True
    url_path = request_dict["PATH_INFO"][len(settings.STATIC_URL):]
    file_path = os.path.join(settings.STATIC_ROOT,url_path)
if is_static:
    try:
        fd = open(file_path,"r")
    except IOError:
        sys.stdout.write("HTTP/1.1 404 Not Found")
        sys.stdout.write("\r\n\r\n")
        sys.exit(0)
    file_content = fd.read()
    fd.close()
    sys.stdout.write("HTTP/1.1 200 OK")
    file_mime_type,_ = mimetypes.guess_type(file_path)
    content_type_hdr = "Content-Type: %s;" % file_mime_type
    sys.stdout.write(content_type_hdr)
    sys.stdout.write("\r\n\r\n")
    sys.stdout.write(file_content)
    sys.stdout.write("\r\n")
    sys.exit(0)

def run_from_xinetd(application):
    environ                      = dict(os.environ.items())
    environ['wsgi.input']        = StringIO(request_body)
    environ['wsgi.errors']       = sys.stderr
    environ['wsgi.version']      = (1,0)
    environ['wsgi.multithread']  = False
    environ['wsgi.multiprocess'] = True
    environ['wsgi.run_once']     = True
    if environ.get('HTTPS','off') in ('on','1'):
        environ['wsgi.url_scheme'] = 'https'
    else:
        environ['wsgi.url_scheme'] = 'http'

    headers_set  = []
    headers_sent = []

    def write(data):
        if not headers_set:
             raise AssertionError("write() before start_response()")
        elif not headers_sent:
             # Before the first output, send the stored headers
             status, response_headers = headers_sent[:] = headers_set
             header_1 = 'HTTP/1.1  %s\r\n' % status
             sys.stdout.write(header_1)
             for header in response_headers:
                 sys.stdout.write('%s: %s\r\n' % header)
             sys.stdout.write('\r\n')
        sys.stdout.write(data)
        sys.stdout.flush()

    def start_response(status,response_headers,exc_info=None):
        if exc_info:
            try:
                if headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None     # avoid dangling circular ref
        elif headers_set:
            raise AssertionError("Headers already set!")
        headers_set[:] = [status,response_headers]
        return write
    result = application(environ,start_response)
    try:
        for data in result:
            if data:    # don't send headers until body appears
                write(data)
        if not headers_sent:
            write('')   # send headers now if body was empty
    finally:
        if hasattr(result,'close'):
            result.close()

run_from_xinetd(django.core.handlers.wsgi.WSGIHandler())
