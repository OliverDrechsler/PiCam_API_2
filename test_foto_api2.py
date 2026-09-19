import unittest
from unittest.mock import MagicMock, patch

import foto_api
from foto_api import PHOTO_DIR, flask_app, take_foto, validate_photo_request


class TestFotoAPIValidation(unittest.TestCase):
    def setUp(self):
        self.app = flask_app.test_client()
        self.app.testing = True

    def test_post_missing_field(self):
        response = self.app.post(
            "/foto/",
            json={
                "width": 640,
                "height": 480,
                "rotation": 0,
                "exposure": "auto",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Missing required field: iso", response.data)

    def test_post_invalid_iso(self):
        response = self.app.post(
            "/foto/",
            json={
                "width": 640,
                "height": 480,
                "rotation": 0,
                "exposure": "auto",
                "iso": 5000,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"iso must be an integer between 0 and 800", response.data)

    def test_validate_photo_request_accepts_numeric_exposure(self):
        result = validate_photo_request(
            {
                "width": 640,
                "height": 480,
                "rotation": 90,
                "exposure": "5000",
                "iso": 100,
            }
        )
        self.assertEqual(result["exposure"], "5000")

    @patch.object(foto_api, "Picamera2")
    @patch("foto_api.Image.open")
    def test_take_foto_no_rotation(self, mock_image_open, mock_picamera):
        foto_api.picam2 = None
        foto_api.camera_size = None
        mock_picam_instance = MagicMock()
        mock_picamera.return_value = mock_picam_instance
        mock_request = MagicMock()
        mock_picam_instance.capture_request.return_value = mock_request

        take_foto(640, 480, 0, "auto", 100, PHOTO_DIR / "test.jpg")

        mock_picam_instance.create_still_configuration.assert_called_once()
        mock_picam_instance.start.assert_called_once()
        mock_picam_instance.set_controls.assert_called_once_with({"AeEnable": True, "AnalogueGain": 1.0})
        mock_request.save.assert_called_once_with("main", str((PHOTO_DIR / "test.jpg").resolve()))
        mock_request.get_metadata.assert_called_once()
        mock_request.release.assert_called_once()
        mock_image_open.assert_called_once()

    @patch.object(foto_api, "Picamera2")
    @patch("foto_api.Image.open")
    def test_take_foto_with_rotation(self, mock_image_open, mock_picamera):
        foto_api.picam2 = None
        foto_api.camera_size = None
        mock_picam_instance = MagicMock()
        mock_picamera.return_value = mock_picam_instance
        mock_picam_instance.capture_request.return_value = MagicMock()
        mock_image = MagicMock()
        mock_image_open.return_value.__enter__.return_value = mock_image

        take_foto(640, 480, 90, "auto", 100, PHOTO_DIR / "rotated.jpg")

        mock_image.rotate.assert_called_once_with(90, expand=True)


if __name__ == "__main__":
    unittest.main()
