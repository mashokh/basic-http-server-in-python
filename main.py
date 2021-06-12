from socket import *
from threading import Thread
import requests
from email.parser import BytesParser
import os
from os import walk
import json
import magic
import urllib
from datetime import date


def open_socket():
    jFile = open('config.json', )
    data = json.load(jFile)
    jFile.close()
    ip_port_pairs, port_vhost_pairs = read_config_file(data)
    sockets = {}
    count = 0
    for key in ip_port_pairs:
        count += 1
        sockets[("socket:" + str(key))] = socket(AF_INET, SOCK_STREAM)
        addr = (ip_port_pairs[key], key)
        sockets[("socket:" + str(key))].bind(addr)
        sockets[("socket:" + str(key))].listen()
    for i in range(0, 1024):
        for key in sockets:
            tmp_thread = Thread(target=listen_client, args=(
                sockets[key], port_vhost_pairs))
            tmp_thread.start()


def read_config_file(data):
    ip_port_pairs = {}
    port_vhost_pairs = {}
    for items in data['server']:
        ip_port_pairs[items['port']] = items['ip']
        port_vhost_pairs[items['vhost']] = items['port']
    return ip_port_pairs, port_vhost_pairs


def listen_client(curr_socket, port_vhost_pairs):
    client_socket, client_address = curr_socket.accept()
    client_request = client_socket.recv(2048)
    parse_request(client_request, client_socket, port_vhost_pairs)


def parse_request(request_text, client_socket, port_vhost_pairs):
    method = request_text.split(b'\r\n')[0]
    request_line, headers_alone = request_text.split(b'\r\n', 1)
    headers = BytesParser().parsebytes(headers_alone)
    proccess_request(method, headers, client_socket, port_vhost_pairs)


def proccess_request(method, headers, client_socket, port_vhost_pairs):
    host = headers['Host'].split(':')[0]
    curr_port = headers['Host'][len(host) + 1:]
    loc = host + method.decode('UTF-8').split(' ')[1]
    curr = os.path.abspath(loc)
    curr = curr.replace("%20", " ")
    connection_type = "keep-alive" if headers["Connection"] == 'keep-alive' else "close"
    range_header = headers['Range']
    accept_range = str(range_header).split(
        '=')[0] if range_header is not None else "None"
    try:
        content_range = range_header.split('=')[1]
        begin = content_range.split('-')[0]
        end = content_range.split('-')[1]
    except:
        content_range = None
    f = ""
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(curr)
    except:
        file_type = None
    if host in port_vhost_pairs and str(curr_port) == str(port_vhost_pairs[host]):
        if os.path.isdir(curr):
            f = directory_response(
                [k for k in os.listdir(curr)], loc.split("/")[1])
        else:
            try:
                with open(curr, "rb") as my_file:
                    f = my_file.read()
                if content_range is not None:
                    if end != "":
                        f = f[int(begin):int(end) + 1]
                    else:
                        f = f[int(begin):]
            except:
                create_response(client_socket, f, file_type,
                                connection_type, content_range, 404, "GET")
                return
        method_type = method.decode('UTF-8').split('/')[0]
        if "GET" in method_type:
            create_response(client_socket, f, file_type,
                            connection_type, content_range, 200, "GET")
        elif "HEAD" in method_type:
            create_response(client_socket, f, file_type,
                            connection_type, content_range, 200, "HEAD")
    else:
        create_response(client_socket, f, file_type,
                        connection_type, content_range, 404, "GET")


def create_response(client_socket, f, file_type, connection_type, content_range, code, method):
    resp = "REQUESTED DOMAIN NOT FOUND"
    if code == 404:
        response_code = "404 Not Found"
        file_type = "text/plain"
    else:
        response_code = "200 OK"

    server = "Python"
    curr_date = str(date.today())
    content_length = str(len(f)) if code == 200 else str(len(resp))
    etag = "abc123"
    file_type = "text/html" if file_type is None else file_type
    send_response(client_socket, f, file_type, connection_type, content_range,
                  response_code, code, method, server, curr_date, content_length, etag, resp)


def send_response(client_socket, f, file_type, connection_type, content_range, response_code, code, method, server, curr_date, content_length, etag, resp):
    client_socket.send(("HTTP/1.1 " + response_code + "\r\n"
                        + "server: " + server + "\r\n"
                        + "date: " + curr_date + "\r\n"
                        + "content-length:" + content_length + "\r\n"
                        + "content-type: " + file_type + "\r\n"
                        + "etag: " + etag + "\r\n"
                        + "Connection: " + connection_type + "\r\n"
                        + "ACCEPT-RANGES: bytes\r\n").encode('UTF-8'))
    if content_range is not None:
        client_socket.send(
            ("Content-Range: bytes " + content_range + "\r\n").encode('UTF-8'))
    if connection_type == "keep-alive":
        client_socket.send(("keep-alive: timeout=5\r\n").encode('UTF-8'))
        client_socket.settimeout(5)
        send_body(f, code, method, resp, client_socket)
    else:
        send_body(f, code, method, resp, client_socket)
        client_socket.close()


def send_body(f, code, method, resp, client_socket):
    if code == 200 and method != 'HEAD':
        client_socket.send("\r\n".encode('UTF-8'))
        if isinstance(f, str):
            client_socket.send(f.encode('UTF-8'))
        else:
            client_socket.send(f)
    else:
        client_socket.send("\r\n".encode('UTF-8'))
        client_socket.send(resp.encode('UTF-8'))


def directory_response(files, directory):
    body = ""
    for file in files:
        body += '<li> <a href="' + directory + '/' + file + '">' + file + '</a></li>\n'

    html_trpple_quoted = """
    <!DOCTYPE html>
    <html>
        <head>
            <body>
                <header>
                    """ + body + """
                </header>
            </body>
        </head>
    </html>
    """

    return html_trpple_quoted


open_socket()
