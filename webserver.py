#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from datetime import datetime
import time
import os

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _set_404_response(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
      #  logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        if str(self.path) == "/config":
            self._set_response()
            self.wfile.write((str(monitor_period) + "|" + str(file_size) + "|" + str(test_time) + "|" + str(terminate_batch) + "|" + str(time.time())).encode('utf-8'))
        elif str(self.path) == "/work":
            self._set_response()
            self.wfile.write((str(current_batch) + "|" + str(time.time())).encode('utf-8'))
        elif str(self.path) == "/purgelog":
            self._set_response()
            os.remove("perflog.csv")
            self.wfile.write("Log has been purged".encode("utf-8"))
        elif str(self.path) == "/showlog":
            self._set_response()
            temp_perflog = open("perflog.csv","r")
            perf_content = temp_perflog.readlines()
            temp_perflog.close()
            self.wfile.write("".join(perf_content).encode("utf-8"))
        else:
            self._set_404_response()
            self.wfile.write("NOT FOUND.  GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):

        global current_batch
        global monitor_period
        global file_size
        global test_time
        global terminate_batch

        if self.path == "/metrics":
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself
            perflog = open("perflog.csv", "a")
            perflog.write(str(time.time()))
            perflog.write("|")
            perflog.write(post_data.decode("utf-8"))
            perflog.write("\n")
            perflog.close()

            self._set_response()
            self.wfile.write(str(time.time()).encode("utf-8"))  #return time signal so there is a chance logs match
        elif self.path == "/work":
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself
            current_batch = int(post_data.decode("utf-8"))
            self._set_response()
            self.wfile.write(str(time.time()).encode("utf-8"))  #return time signal so there is a chance logs match
        elif self.path == "/config":
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            config_data = self.rfile.read(content_length) # <--- Gets the data itself
            config_data_parts = config_data.decode("utf-8").split("|")
            monitor_period = int(config_data_parts[0])
            file_size = int(config_data_parts[1])
            test_time = int(config_data_parts[2])
            terminate_batch = int(config_data_parts[3])
            self._set_response()
            self.wfile.write(str(time.time()).encode("utf-8"))  #return time signal so there is a chance logs match
        else:
            self._set_404_response()
            self.wfile.write("NOT FOUND.  POST request for {}".format(self.path).encode('utf-8'))



def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')



if __name__ == '__main__':
    from sys import argv

    monitor_period = 15 # Seconds to sleep between test samples
    file_size = 25000 # Size of file to send in bytes
    test_time = 1800  # Total test time in seconds
    terminate_batch = 99
    current_batch = 0


    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()