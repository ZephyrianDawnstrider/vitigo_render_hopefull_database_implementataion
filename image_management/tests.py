import io
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from .models import PatientImage


class PatientImageMetadataTests(SimpleTestCase):
    def test_metadata_for_supported_upload_formats(self):
        for image_format, extension in [('PNG', 'png'), ('JPEG', 'jpg')]:
            with self.subTest(image_format=image_format):
                stream = io.BytesIO()
                Image.new('RGB', (17, 23), 'blue').save(stream, image_format)
                content = stream.getvalue()
                patient_image = PatientImage(image_file=SimpleUploadedFile('test.' + extension, content))
                patient_image.extract_metadata()
                self.assertEqual((patient_image.width, patient_image.height), (17, 23))
                self.assertEqual(patient_image.file_size, len(content))

    def test_no_file_does_not_extract_metadata(self):
        patient_image = PatientImage()
        patient_image.extract_metadata()
        self.assertIsNone(patient_image.width)
        self.assertIsNone(patient_image.height)
