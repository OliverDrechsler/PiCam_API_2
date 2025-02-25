import unittest
from unittest.mock import patch, MagicMock
import json
import os
from foto_api import flask_app, take_foto


class TestFotoAPI(unittest.TestCase):
    def setUp(self):
        self.app = flask_app.test_client()
        self.app.testing = True
    
    def test_get_nonexistent_file(self):
        """Test GET request for a non-existent file"""
        response = self.app.get('/foto/?filename=nonexistent.jpg')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'File not found')
    
    @patch('foto_api.os.path.exists')
    @patch('foto_api.send_file')
    def test_get_existing_file(self, mock_send_file, mock_exists):
        """Test GET request for an existing file"""
        mock_exists.return_value = True
        mock_send_file.return_value = 'file_content'
        
        response = self.app.get('/foto/?filename=test.jpg')
        self.assertEqual(response.status_code, 200)
        mock_send_file.assert_called_once()
    
    def test_post_missing_field(self):
        """Test POST request with missing required field"""
        test_data = {
            'width': 640,
            'height': 480,
            'rotation': 0,
            'exposure': 'auto',
            # 'iso' field missing
            'filename': 'test.jpg'
        }
        response = self.app.post('/foto/', 
                               json=test_data,
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @patch('foto_api.take_foto')
    def test_post_valid_data(self, mock_take_foto):
        """Test POST request with valid data"""
        test_data = {
            'width': 640,
            'height': 480,
            'rotation': 0,
            'exposure': 'auto',
            'iso': 100,
            'filename': '/tmp/foto.jpg'  # Fügen Sie das fehlende Argument hinzu
        }
        response = self.app.post('/foto/',
                                 json=test_data,
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['foto resolution'], '640x480')
        mock_take_foto.assert_called_once_with(**test_data)

    @patch('foto_api.Picamera2')
    @patch('foto_api.Image.open')
    def test_take_foto_no_rotation(self, mock_image_open, mock_picamera):
        """Test take_foto function with no rotation"""
        mock_picam_instance = MagicMock()
        mock_picamera.return_value = mock_picam_instance
        
        take_foto(640, 480, 0, 'auto', 100, 'test.jpg')
        
        mock_picam_instance.create_still_configuration.assert_called_once()
        mock_picam_instance.capture_file.assert_called_once()
        mock_image_open.assert_called_once()
    
    @patch('foto_api.Picamera2')
    @patch('foto_api.Image.open')
    def test_take_foto_with_rotation(self, mock_image_open, mock_picamera):
        """Test take_foto function with rotation"""
        mock_picam_instance = MagicMock()
        mock_picamera.return_value = mock_picam_instance
        mock_image = MagicMock()
        mock_image_open.return_value.__enter__.return_value = mock_image
        
        take_foto(640, 480, 90, 'auto', 100, 'test.jpg')
        
        mock_image.rotate.assert_called_once_with(90, expand=True)

if __name__ == '__main__':
    unittest.main()