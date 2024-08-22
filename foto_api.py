#!/usr/bin/env python3
import os
from flask import Flask, request, send_file
from flask_restx import Api, Resource, fields
try:
    from picamera2 import Picamera2
    from libcamera import Transform
except ImportError:
    Picamera2 = None
from PIL import Image
import time

# Initialize Flask app
flask_app = Flask(__name__)
app = Api(
    app=flask_app,
    version="1.0",
    title="Pi Camera Foto API",
    description="Takes photos and allows downloading them"
)

# Define namespace
name_space = app.namespace('foto', description='Foto API 2')

# Define data model for the API
model = app.model(
    'Foto Properties',
    {
        'width': fields.Integer(
            default=640,
            required=False,
            description="Width of the photo in pixels",
            help="Specify the width in pixels like 640x480 means 640 in width"
        ),
        'height': fields.Integer(
            default=480,
            required=False,
            description="Height of the photo in pixels",
            help="Specify the height in pixels like 640x480 means 480 in height"
        ),
        'rotation': fields.Integer(
            default=0,
            required=False,
            description="Photo rotation in degrees",
            help="Photo rotation in degrees, should be 0, 90, 180, or 270"
        ),
        'exposure': fields.String(
            default='auto',
            required=False,
            description="Photo exposure mode or exposure time",
            help="Photo mode auto, night, sports, etc., or exposure time in microseconds"
        ),
        'iso': fields.Integer(
            default=100,
            required=False,
            description="Photo ISO",
            help="ISO Mode 0 ... 800"
        ),
        'filename': fields.String(
            default='foto.jpg',
            required=False,
            description="Filename",
            help="Photo filename"
        ),
    }
)

@name_space.route("/")
class MainClass(Resource):

    @app.doc(
        responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'},
        params={'filename': 'Specify the photo filename'}
    )
    def get(self):
        filename = request.args.get('filename', default='foto.jpg', type=str)
        try:
            file_path = os.path.join('/tmp/', filename)
            if os.path.exists(file_path):
                response = send_file(file_path, as_attachment=True)
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    # Log this if needed, but continue
                    pass
                return response
            else:
                # Return 404 not found
                return {"message": "File not found", "statusCode": "404"}, 404

        except Exception as e:
            # Log the actual exception here if needed for debugging
            name_space.abort(
                500, e.__doc__, status="Could not retrieve information", statusCode="500"
            )
    @app.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Mapping Key Error'})
    @app.expect(model)
    def post(self):
        try:
            json_input = request.get_json()
            # Ensure all expected keys are present
            required_fields = ['width', 'height', 'rotation', 'exposure', 'iso', 'filename']
            for field in required_fields:
                if field not in json_input:
                    return {"message": f"Missing required field: {field}", "statusCode": "400"}, 400

            take_foto(
                width=json_input['width'],
                height=json_input['height'],
                rotation=json_input['rotation'],
                exposure=json_input['exposure'],
                iso=json_input['iso'],
                filename=json_input['filename']
            )
            return {
                "status": "new foto created",
                "foto resolution": f"{json_input['width']}x{json_input['height']}",
                "foto rotation": json_input['rotation'],
                "exposure mode": json_input['exposure'],
                "iso": json_input['iso'],
                "filename": json_input['filename']
            }

        except Exception as e:
            name_space.abort(
                400, e.__doc__, status="Could not save information", statusCode="400"
            )

def take_foto(width: int, height: int, rotation: int, exposure: str, iso: int, filename: str):
    print(width, height, rotation, exposure, iso, filename)
    if Picamera2 is None:
        raise RuntimeError("Picamera2 library is not installed.")
    picam2 = Picamera2()
    camera_config = picam2.create_still_configuration(main={"size": (width, height)}, buffer_count=1)
    print(camera_config)
    picam2.configure(camera_config)
    picam2.start()
    file_path = os.path.join('/tmp/', filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    picam2.capture_file(file_path)
    picam2.stop()
    picam2.close()

    with Image.open(file_path) as img:
        if rotation != 0:
            rotated_img = img.rotate(rotation, expand=True)
            rotated_img.save(file_path)


if __name__ == "__main__":
    flask_app.run(
        host=os.getenv('IP', '0.0.0.0'),
        port=8000,
        debug=True
    )
