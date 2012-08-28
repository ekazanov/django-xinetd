#!/home/evgeny/projects/079-django-tmpl-bin/www/env/bin/python
"""
Script to deploy Django using xinetd.
"""

import os, sys, re
import mimetypes
import django.core.handlers.wsgi
from django.utils import importlib

sys.path.append("/home/evgeny/projects/079-django-tmpl-bin/www/insert_your_project_name_here")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insert_your_project_name_here.settings")

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

# Request parsing code
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

class HTTPRequest(BaseHTTPRequestHandler):
    """
    http://stackoverflow.com/questions/4685217/parse-raw-http-headers
    """
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

request = HTTPRequest(request_text)

# Process static files
if request.path.startswith(settings.STATIC_URL):
    url_path = request.path[len(settings.STATIC_URL):]
    file_path = os.path.join(settings.STATIC_ROOT,url_path)
    fd = open(file_path,"r")
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

request_headers_lines = str(request.headers).split("\r\n")
request_headers = {}
for l in request_headers_lines:
    if len(l) != 0:
        k,v = l.split(": ")
        request_headers[k] = v

os.environ["SERVER_NAME"],os.environ["SERVER_PORT"] = request_headers["Host"].split(":")    
os.environ["REQUEST_METHOD"] = request.command
os.environ["PATH_INFO"] = request.path
os.environ["SERVER_PROTOCOL"] = request.request_version
if re.findall('\?',request.path):
    path,query_str = request.path.split('?')
    os.environ["QUERY_STRING"] = query_str

def set_env_var_from_header(env_var_name,header_name,headers_dict):
    if headers_dict.has_key(header_name):
        os.environ[env_var_name] = headers_dict[header_name]
        return
    else:
        return

set_env_var_from_header("HTTP_COOKIE","Cookie",request_headers)
set_env_var_from_header("CONTENT_LENGTH","Content-Length",request_headers)
set_env_var_from_header("CONTENT_TYPE","Content-Type",request_headers)

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
