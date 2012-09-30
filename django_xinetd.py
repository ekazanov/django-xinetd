#!/usr/bin/python
"""
Script to deploy Django using xinetd.
"""
import os, sys, re
import mimetypes
import logging
import logging.handlers
from StringIO import StringIO
import django.core.handlers.wsgi
from django.utils import importlib

DOCUMENT_ROOT = "/path_to_your_project/insert_your_project_name_here/static/documentroot"
STATIC_FILES = ["/favicon.ico","/robots.txt"]
PROJECT_PATH = "/path_to_your_project/insert_your_project_name_here"
DJANGO_SETTINGS_MODULE = "insert_your_project_name_here.settings"
LOGGING_NAME = 'insert_your_logging_name'

logger = logging.getLogger(LOGGING_NAME)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(process)s [%(levelname)s] %(name)s: %(message)s')
handler = logging.handlers.SysLogHandler(address = '/dev/log')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.debug("Start")

sys.path.append(PROJECT_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

try:
    settings = importlib.import_module(os.environ["DJANGO_SETTINGS_MODULE"])
except Exception, e:
    logger.error("Can not import module: DJANGO_SETTINGS_MODULE")
    logger.error("Exception: " + str(e))
    logger.error("Exit")
    sys.exit(1)

def get_request():
    logger.debug("get_request()")
    request = ""
    request_body = ""
    new_line = ""
    logger.debug("get_request() - Get headers start")
    while True:
        # GET headers
        new_line = sys.stdin.readline()
        if new_line == "":
            return(None,None)
        request += new_line
        if request.endswith("\r\n\r\n") or request.endswith("\n\n"):
            break
    logger.debug("get_request() - Get headers end")
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
    logger.debug("get_request() return")
    return (request,request_body)

try:
    request_text,request_body = get_request()
except Exception, e:
    logger.error("Can not get request")
    logger.error("Exception: " + str(e))
    logger.error("Exit")
    sys.exit(1)

if request_text == None:
    logger.error("Can not get request")
    logger.error("Exit")
    sys.exit(1)

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
logger.debug("Process static files: Start")
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
        logger.debug("Static file reading error: " + file_path)
        logger.debug("Exit")
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
    
    logger.debug("Process static files: End")
    logger.debug("Exit")
    sys.exit(0)

def run_from_xinetd(application):
    logger.debug("run_from_xinetd()")
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
        logger.debug("write()")
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
        logger.debug("start_response()")
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

try:
    run_from_xinetd(django.core.handlers.wsgi.WSGIHandler())
except Exception, e:
    logger.error("Exception during run_from_xinetd()")
    logger.error("Exception: " + str(e))
    logger.error("Exit")
    sys.exit(1)
