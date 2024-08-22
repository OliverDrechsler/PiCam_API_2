import os
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_testing import TestCase
from foto_api import flask_app, take_foto


class TestFotoAPI(TestCase):
    def create_app(self):
        # Configure Flask to run in testing mode
        flask_app.config['TESTING'] = True
        return flask_app

    @patch('foto_api.os.path.exists')
    @patch('foto_api.send_file')
    def test_get_foto_success(self, mock_send_file, mock_os_path_exists):
        """Test GET /foto/ when file exists."""
        # Arrange
        mock_os_path_exists.return_value = True
        mock_send_file.return_value = "File Content"

        # Act
        response = self.client.get('/foto/', query_string={'filename': 'test.jpg'})

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b'"File Content"\n', response.data)
        mock_send_file.assert_called_once_with('/tmp/test.jpg', as_attachment=True)

    @patch('foto_api.os.path.exists')
    def test_get_foto_file_not_found(self, mock_os_path_exists):
        """Test GET /foto/ when file does not exist."""
        # Arrange
        mock_os_path_exists.return_value = False

        # Act
        response = self.client.get('/foto/', query_string={'filename': 'test.jpg'})

        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"File not found", response.data)

    @patch('foto_api.take_foto')
    def test_post_foto_success(self, mock_take_foto):
        """Test POST /foto/ with valid data."""
        # Arrange
        mock_take_foto.return_value = None
        payload = {
            "width": 640,
            "height": 480,
            "rotation": 0,
            "exposure": "auto",
            "iso": 100,
            "filename": "test.jpg"
        }

        # Act
        response = self.client.post('/foto/', json=payload)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"new foto created", response.data)
        mock_take_foto.assert_called_once_with(
            width=640,
            height=480,
            rotation=0,
            exposure="auto",
            iso=100,
            filename="test.jpg"
        )

    @patch('foto_api.take_foto')
    def test_post_foto_missing_key(self, mock_take_foto):
        """Test POST /foto/ with missing required data."""
        # Arrange
        mock_take_foto.return_value = None
        payload = {
            "height": 480,
            "rotation": 0,
            "exposure": "auto",
            "iso": 100,
            "filename": "test.jpg"
        }

        # Act
        response = self.client.post('/foto/', json=payload)

        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Missing required field: width", response.data)
        mock_take_foto.assert_not_called()

    @patch('foto_api.Picamera2', None)
    def test_take_foto_picamera_not_installed(self):
        """Test take_foto when Picamera2 library is not installed."""
        with self.assertRaises(RuntimeError) as context:
            take_foto(640, 480, 0, "auto", 100, "test.jpg")
        self.assertEqual(str(context.exception), "Picamera2 library is not installed.")


if __name__ == '__main__':
    unittest.main()
