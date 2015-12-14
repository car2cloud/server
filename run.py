import os
import json
import time
import base64
import cPickle
import pickle
import datetime
import logging
import flask
import requests
import werkzeug
import optparse
import tornado.wsgi
import tornado.httpserver
import numpy as np
import pandas as pd
from PIL import Image
import cStringIO as StringIO
import urllib
import exifutil
import shutil
import math

REPO_DIRNAME = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../..')
UPLOAD_FOLDER = '/tmp/uploaded_frames'
ALLOWED_IMAGE_EXTENSIONS = set(['png', 'bmp', 'jpg', 'jpe', 'jpeg', 'gif'])

# Obtain the flask app object
app = flask.Flask(__name__)

# global gps dictionary: gps coords are keys and values are images
gps_view = {}

@app.route('/')
def index():
    return flask.render_template('index.html', has_result=False)


@app.route('/android_post', methods=['POST'])
def process_android_upload():
    # Get the parsed contents of the form data
    if flask.request.headers['Content-Type'] == 'application/json':
        try:

            image_string = flask.request.json['image']
            image_filename = flask.request.json['filename']
            gps_coords = (flask.request.json['longitude'], flask.request.json['latitude'])

            filename_ = str(datetime.datetime.now()).replace(' ', '_') + '_' +\
                werkzeug.secure_filename(image_filename)

            abs_filename = os.path.join(UPLOAD_FOLDER, filename_)
            image_data = decode_image(image_string)

            with open(abs_filename, 'wb') as f:
                f.write(image_data)
            logging.info('Saving to %s.', abs_filename)

            # for now only keep the latest image for each pair of gps coords
            gps_view[gps_coords] = abs_filename

        except Exception as err:
            logging.info('Uploaded image from Android open error: %s', err)
    else:
        logging.info('Unaccepted format')

    return ('', 204)

def decode_image(base64_image):
    # decode Base64 image data
    enc_data = base64.b64decode(base64_image)
    return enc_data


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS
    )

# use haversine formula to calculate distance between two gps coords
def gps_distance(gps1, gps2):
    radius = 3959 # in miles...6371 in km

    dlat = math.radians(gps1[0]-gps2[0])
    dlon = math.radians(gps2[0]-gps2[1])
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(gps1[0])) \
        * math.cos(math.radians(gps1[0])) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c
    return d

def start_tornado(app, port=5000):
    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    print("Tornado server starting on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()

def start_from_terminal(app):
    """
    Parse command line options and start the server.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        '-d', '--debug',
        help="enable debug mode",
        action="store_true", default=False)
    parser.add_option(
        '-p', '--port',
        help="which port to serve content on",
        type='int', default=5000)
    parser.add_option(
        '-g', '--gpu',
        help="use gpu mode",
        action='store_true', default=False)

    opts, args = parser.parse_args()

    if opts.debug:
        app.run(debug=True, host='0.0.0.0', port=opts.port)
    else:
        start_tornado(app, opts.port)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    try:
        start_from_terminal(app)
    finally:
        shutil.rmtree('/tmp/uploaded_frames')
