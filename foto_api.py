#!/usr/bin/env python3
import os
import threading
import uuid
from pathlib import Path

from flask import Flask, request, send_file
from PIL import Image

try:
    from flask_restx import Api, Resource, fields
except ImportError:
    class Resource:
        pass

    class _FieldFactory:
        @staticmethod
        def Integer(**kwargs):
            return kwargs

        @staticmethod
        def String(**kwargs):
            return kwargs

    class Api:
        def __init__(self, app, **kwargs):
            self.app = app

        def namespace(self, name, description=None):
            api_app = self.app
            base_path = f"/{name.strip('/')}"

            class _Namespace:
                def route(self, rule):
                    def decorator(resource_cls):
                        endpoint_rule = f"{base_path}/{rule.lstrip('/')}" if rule != "/" else f"{base_path}/"
                        view = resource_cls.as_view(f"{resource_cls.__name__}_{endpoint_rule}")
                        methods = [
                            method.upper()
                            for method in ("get", "post", "put", "delete", "patch")
                            if hasattr(resource_cls, method)
                        ]
                        api_app.add_url_rule(endpoint_rule, view_func=view, methods=methods)
                        return resource_cls

                    return decorator

            return _Namespace()

        def model(self, _name, schema):
            return schema

        def doc(self, **_kwargs):
            def decorator(func):
                return func

            return decorator

        def expect(self, _model):
            def decorator(func):
                return func

            return decorator

    from flask.views import MethodView

    class Resource(MethodView):
        pass

    fields = _FieldFactory()

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None


PHOTO_DIR = Path("/tmp/picam_api")
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

MIN_WIDTH = 64
MAX_WIDTH = 3280
MIN_HEIGHT = 64
MAX_HEIGHT = 2464
ALLOWED_ROTATIONS = {0, 90, 180, 270}
MIN_ISO = 0
MAX_ISO = 800
MAX_EXPOSURE_US = 1_000_000
ALLOWED_EXPOSURES = {"auto"}

photo_store = {}
photo_store_lock = threading.Lock()
camera_lock = threading.Lock()


flask_app = Flask(__name__)
app = Api(
    app=flask_app,
    version="2.0",
    title="Pi Camera Foto API",
    description="Takes photos and allows downloading them",
)

name_space = app.namespace("foto", description="Foto API 2")

model = app.model(
    "Foto Properties",
    {
        "width": fields.Integer(
            default=640,
            required=True,
            description="Width of the photo in pixels",
        ),
        "height": fields.Integer(
            default=480,
            required=True,
            description="Height of the photo in pixels",
        ),
        "rotation": fields.Integer(
            default=0,
            required=True,
            description="Photo rotation in degrees. Allowed: 0, 90, 180, 270",
        ),
        "exposure": fields.String(
            default="auto",
            required=True,
            description="Exposure mode 'auto' or exposure time in microseconds",
        ),
        "iso": fields.Integer(
            default=100,
            required=True,
            description="ISO value from 0 to 800",
        ),
    },
)


def _bad_request(message: str):
    return {"message": message, "statusCode": "400"}, 400


def _normalize_exposure(exposure):
    if exposure in ALLOWED_EXPOSURES:
        return exposure

    if isinstance(exposure, int):
        exposure_value = exposure
    elif isinstance(exposure, str) and exposure.isdigit():
        exposure_value = int(exposure)
    else:
        raise ValueError("exposure must be 'auto' or a positive integer in microseconds")

    if not 1 <= exposure_value <= MAX_EXPOSURE_US:
        raise ValueError(f"exposure must be between 1 and {MAX_EXPOSURE_US} microseconds")
    return str(exposure_value)


def validate_photo_request(json_input):
    if not isinstance(json_input, dict):
        raise ValueError("JSON request body is required")

    required_fields = ["width", "height", "rotation", "exposure", "iso"]
    for field in required_fields:
        if field not in json_input:
            raise ValueError(f"Missing required field: {field}")

    width = json_input["width"]
    height = json_input["height"]
    rotation = json_input["rotation"]
    iso = json_input["iso"]

    if not isinstance(width, int) or not MIN_WIDTH <= width <= MAX_WIDTH:
        raise ValueError(f"width must be an integer between {MIN_WIDTH} and {MAX_WIDTH}")
    if not isinstance(height, int) or not MIN_HEIGHT <= height <= MAX_HEIGHT:
        raise ValueError(f"height must be an integer between {MIN_HEIGHT} and {MAX_HEIGHT}")
    if not isinstance(rotation, int) or rotation not in ALLOWED_ROTATIONS:
        raise ValueError("rotation must be one of 0, 90, 180, 270")
    if not isinstance(iso, int) or not MIN_ISO <= iso <= MAX_ISO:
        raise ValueError(f"iso must be an integer between {MIN_ISO} and {MAX_ISO}")

    exposure = _normalize_exposure(json_input["exposure"])

    return {
        "width": width,
        "height": height,
        "rotation": rotation,
        "exposure": exposure,
        "iso": iso,
    }


def create_photo_path(photo_id: str) -> Path:
    filename = f"{photo_id}.jpg"
    file_path = (PHOTO_DIR / filename).resolve()
    if file_path.parent != PHOTO_DIR.resolve():
        raise ValueError("Invalid photo filename")
    return file_path


def pop_photo_path(photo_id: str):
    with photo_store_lock:
        return photo_store.pop(photo_id, None)


@name_space.route("/")
class MainClass(Resource):
    @app.doc(
        params={"photo_id": "Identifier returned by POST /foto/"},
        responses={200: "OK", 400: "Invalid Argument", 404: "Not Found", 500: "Internal Server Error"},
    )
    def get(self):
        photo_id = request.args.get("photo_id", "").strip()
        if not photo_id:
            return _bad_request("photo_id query parameter is required")

        file_path = pop_photo_path(photo_id)
        if file_path is None:
            return {"message": "Photo not found", "statusCode": "404"}, 404

        if not file_path.exists():
            return {"message": "Photo file not found", "statusCode": "404"}, 404

        try:
            response = send_file(file_path, as_attachment=True, download_name=file_path.name)

            def cleanup():
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    flask_app.logger.warning("Could not remove photo file %s", file_path)

            response.call_on_close(cleanup)
            return response
        except Exception:
            flask_app.logger.exception("Failed to deliver photo %s", photo_id)
            return {"message": "Could not retrieve photo", "statusCode": "500"}, 500

    @app.doc(responses={200: "OK", 400: "Invalid Argument", 500: "Internal Server Error"})
    @app.expect(model)
    def post(self):
        try:
            photo_request = validate_photo_request(request.get_json())
            photo_id = uuid.uuid4().hex
            file_path = create_photo_path(photo_id)

            take_foto(
                width=photo_request["width"],
                height=photo_request["height"],
                rotation=photo_request["rotation"],
                exposure=photo_request["exposure"],
                iso=photo_request["iso"],
                file_path=file_path,
            )
            with photo_store_lock:
                photo_store[photo_id] = file_path

            return {
                "status": "new foto created",
                "photo_id": photo_id,
                "foto resolution": f"{photo_request['width']}x{photo_request['height']}",
                "foto rotation": photo_request["rotation"],
                "exposure mode": photo_request["exposure"],
                "iso": photo_request["iso"],
            }
        except ValueError as exc:
            return _bad_request(str(exc))
        except RuntimeError:
            flask_app.logger.exception("Camera runtime error while creating a photo")
            return {"message": "Could not create photo", "statusCode": "500"}, 500
        except Exception:
            flask_app.logger.exception("Unexpected error while creating a photo")
            return {"message": "Could not create photo", "statusCode": "500"}, 500


def take_foto(width: int, height: int, rotation: int, exposure: str, iso: int, file_path: Path):
    file_path = file_path.resolve()
    if file_path.parent != PHOTO_DIR.resolve():
        raise ValueError("file_path must stay inside the photo directory")

    if Picamera2 is None:
        raise RuntimeError("Picamera2 library is not installed.")

    with camera_lock:
        picam2 = Picamera2()
        try:
            camera_config = picam2.create_still_configuration(
                main={"size": (width, height)},
                buffer_count=1,
            )
            picam2.configure(camera_config)
            picam2.start()
            picam2.capture_file(str(file_path))
        finally:
            try:
                picam2.stop()
            except Exception:
                flask_app.logger.warning("Could not stop camera cleanly")
            picam2.close()

    with Image.open(file_path) as img:
        if rotation != 0:
            rotated_img = img.rotate(rotation, expand=True)
            rotated_img.save(file_path)


if __name__ == "__main__":
    flask_app.run(
        host=os.getenv("IP", "0.0.0.0"),
        port=8000,
        debug=False,
    )
