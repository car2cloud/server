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

@app.route('/', methods=['GET'])
def process_gps_request():
    try:
        logging.info('Request image for gps coords: long=%s, lat=%s',
                    flask.request.args.get('longitude'),
                    flask.request.args.get('latitude'))
    except:
        return ('Request should be of form "/?longitude=x&latitude=y"', 404)

    # Get the requested gps coords from the query string
    requested_gps = (float(flask.request.args.get('longitude')),
                    float(flask.request.args.get('latitude')))

    # get the image file for the closest stored gps coordinates
    image_file = get_closest_image(requested_gps)

    # no closest gps coord (list likely empty), so return 404
    if ( image_file == "" ):
        return ('No stored images at the server!', 404)

    return flask.send_file(image_file, mimetype='image/jpg')

def decode_image(base64_image):
    # decode Base64 image data
    enc_data = base64.b64decode(base64_image)
    return enc_data


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS
    )

# function that iterates through stored gps coords and returns filename for closest one
def get_closest_image(req_gps):
    min_distance = 1000000
    best_image_match = ""
    for stored_gps in gps_view:
        curr_distance = gps_distance(req_gps, stored_gps)
        if (curr_distance < min_distance):
            min_distance = curr_distance
            best_image_match = gps_view[stored_gps]

    return best_image_match

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
