import unittest
from pathlib import Path
from unittest.mock import patch

import foto_api
from foto_api import PHOTO_DIR, flask_app, photo_store, photo_store_lock, take_foto


class TestFotoAPI(unittest.TestCase):
    def setUp(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def tearDown(self):
        with photo_store_lock:
            photo_store.clear()

    def test_get_requires_photo_id(self):
        response = self.client.get("/foto/")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"photo_id query parameter is required", response.data)

    def test_get_photo_not_found(self):
        response = self.client.get("/foto/?photo_id=missing")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Photo not found", response.data)

    @patch("foto_api.send_file")
    def test_get_photo_success(self, mock_send_file):
        photo_id = "photo123"
        file_path = PHOTO_DIR / f"{photo_id}.jpg"
        file_path.touch()
        with photo_store_lock:
            photo_store[photo_id] = file_path

        mock_response = flask_app.response_class("file-content", status=200)
        mock_send_file.return_value = mock_response

        response = self.client.get(f"/foto/?photo_id={photo_id}")

        self.assertEqual(response.status_code, 200)
        mock_send_file.assert_called_once_with(file_path, as_attachment=True, download_name=file_path.name)
        self.assertNotIn(photo_id, photo_store)

    @patch("foto_api.take_foto")
    def test_post_foto_success(self, mock_take_foto):
        payload = {
            "width": 640,
            "height": 480,
            "rotation": 0,
            "exposure": "auto",
            "iso": 100,
        }

        response = self.client.post("/foto/", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["foto resolution"], "640x480")
        self.assertIn("photo_id", data)

        expected_path = (PHOTO_DIR / f"{data['photo_id']}.jpg").resolve()
        mock_take_foto.assert_called_once_with(
            width=640,
            height=480,
            rotation=0,
            exposure="auto",
            iso=100,
            file_path=expected_path,
        )

    @patch("foto_api.take_foto")
    def test_post_foto_invalid_rotation(self, mock_take_foto):
        payload = {
            "width": 640,
            "height": 480,
            "rotation": 45,
            "exposure": "auto",
            "iso": 100,
        }

        response = self.client.post("/foto/", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"rotation must be one of 0, 90, 180, 270", response.data)
        mock_take_foto.assert_not_called()

    def test_take_foto_rejects_outside_photo_directory(self):
        with self.assertRaises(ValueError):
            take_foto(640, 480, 0, "auto", 100, Path("/tmp/not-allowed.jpg"))

    @patch.object(foto_api, "Picamera2", None)
    def test_take_foto_picamera_not_installed(self):
        file_path = PHOTO_DIR / "test.jpg"
        with self.assertRaises(RuntimeError):
            take_foto(640, 480, 0, "auto", 100, file_path)


if __name__ == "__main__":
    unittest.main()
