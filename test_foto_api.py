import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import os

from flask import Flask
from flask_restx import Api
from werkzeug.datastructures import FileStorage

# Import the Flask app for testing
from foto_api import flask_app as app, take_foto

class FotoApiTestCase(unittest.TestCase):

    def setUp(self):
        # Set up a test client
        self.app = app.test_client()
        self.app.testing = True

    @patch('foto_api.os.path.exists')
    @patch('foto_api.send_file')
    @patch('foto_api.os.remove')
    def test_get_existing_file(self, mock_remove, mock_send_file, mock_exists):
        mock_exists.return_value = True
        mock_send_file.return_value = "File content"

        response = self.app.get('/foto/', query_string={'filename': 'test.jpg'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), 'File content')
        mock_remove.assert_called_once_with('/tmp/test.jpg')

    @patch('foto_api.os.path.exists')
    def test_get_non_existing_file(self, mock_exists):
        mock_exists.return_value = False

        response = self.app.get('/foto/', query_string={'filename': 'nonexistent.jpg'})

        self.assertEqual(response.status_code, 500)

    @patch('foto_api.take_foto')
    def test_post_valid_input(self, mock_take_foto):
        mock_take_foto.return_value = None  # Mock the take_foto function

        data = {
            'width': 640,
            'height': 480,
            'rotation': 90,
            'exposure': 'auto',
            'iso': 100,
            'filename': 'test.jpg'
        }

        response = self.app.post('/foto/', json=data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("new foto created", response.json['status'])
        self.assertIn("640x480", response.json['foto resolution'])

    def test_post_invalid_input(self):
        # Missing 'width' field in the input
        data = {
            'height': 480,
            'rotation': 90,
            'exposure': 'auto',
            'iso': 100,
            'filename': 'test.jpg'
        }

        response = self.app.post('/foto/', json=data)

        self.assertEqual(response.status_code, 400)

    @patch('foto_api.Picamera2')
    @patch('foto_api.os.path.exists')
    @patch('foto_api.os.remove')
    def test_take_foto(self, mock_remove, mock_exists, MockPicamera2):
        mock_exists.return_value = False
        mock_cam = MockPicamera2.return_value
        mock_cam.configure = MagicMock()
        mock_cam.capture_file = MagicMock()
        mock_cam.start = MagicMock()
        mock_cam.stop = MagicMock()
        mock_cam.close = MagicMock()

        take_foto(640, 480, 90, 'auto', 100, 'test.jpg')

        mock_cam.configure.assert_called_once()
        mock_cam.capture_file.assert_called_once_with('/tmp/test.jpg')
        mock_cam.start.assert_called_once()
        mock_cam.stop.assert_called_once()
        mock_cam.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
