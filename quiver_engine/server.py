import json
import numpy as np

from flask import Flask, send_from_directory
from flask.json import jsonify
from flask_cors import CORS

from keras.preprocessing import image
from keras.models import Model

from imagenet_utils import preprocess_input
from gevent.wsgi import WSGIServer

from scipy.misc import imsave
from os.path import abspath, relpath
from util import deprocess_image
import tensorflow as tf
graph = tf.get_default_graph()


def get_app(model, temp_folder='./tmp'):

    app = Flask(__name__)
    app.threaded=True
    CORS(app)

    @app.route('/')
    def home():
        return 'quiver home'

    @app.route('/temp-file/<path>')
    def get_temp_file(path):
        return send_from_directory(abspath(temp_folder), path)

    @app.route('/model', methods=['GET'])
    def get_config():
        return jsonify(json.loads(model.to_json()))

    @app.route('/layer/<layer_name>/<input_path>', methods=['GET'])
    def get_layer_outputs(layer_name, input_path):

        layer_model = Model(
            input=model.input,
            output=model.get_layer(layer_name).output
        )

        img_path = input_path
        img = image.load_img(img_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        with graph.as_default():

            layer_outputs = layer_model.predict(x)
            output_files = []

            for z in range(0, layer_outputs.shape[2]):

                img = layer_outputs[0][:, :, z]
                deprocessed = deprocess_image(img)
                filename = get_output_name(temp_folder, layer_name, z)
                output_files.append(
                    relpath(
                        filename,
                        abspath(temp_folder)
                    )
                )
                imsave(filename, deprocessed)

        return jsonify(output_files)

    return app

def run_app(app):
    http_server = WSGIServer(('', 5000), app)
    return http_server.serve_forever()

def launch(model, temp_folder='./tmp', port=5000):
    return run_app(
        get_app(model, temp_folder)
    )

def get_output_name(temp_folder, layer_name, z_idx):
    return temp_folder + '/' + layer_name + '_' + str(z_idx) + '.png'