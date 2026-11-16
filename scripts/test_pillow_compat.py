import ast, io, pathlib, types, unittest
from PIL import Image
from django.conf import settings
settings.configure(USE_I18N=False)
from django.forms import ImageField
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT = pathlib.Path(__file__).resolve().parents[1]
class PillowCompatibility(unittest.TestCase):
    def test_repository_metadata_method_and_django_upload(self):
        for repo in ('.',):
            module = ast.parse((ROOT/repo/'image_management/models.py').read_text())
            cls = next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='PatientImage')
            method = next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='extract_metadata')
            ns={'PILImage':Image}
            exec(compile(ast.Module(body=[method], type_ignores=[]),str(ROOT/repo/'image_management/models.py'),'exec'),ns)
            for fmt, ext in [('PNG','png'),('JPEG','jpg')]:
                with self.subTest(repo=repo,format=fmt):
                    out=io.BytesIO(); Image.new('RGB',(17,23),'blue').save(out,fmt)
                    upload=SimpleUploadedFile('test.'+ext,out.getvalue(),content_type='image/'+ext)
                    ImageField().clean(upload); upload.seek(0)
                    obj=types.SimpleNamespace(image_file=upload)
                    ns['extract_metadata'](obj)
                    self.assertEqual((obj.width,obj.height,obj.file_size),(17,23,len(out.getvalue())))
    def test_invalid_image_rejected(self):
        with self.assertRaises(ValidationError):
            ImageField().clean(SimpleUploadedFile('invalid.jpg',b'not an image'))
    def test_reportlab_image_pdf(self):
        out=io.BytesIO(); c=canvas.Canvas(out)
        c.drawImage(ImageReader(Image.new('RGB',(17,23),'blue')),0,0); c.save()
        self.assertTrue(out.getvalue().startswith(b'%PDF'))
    def test_compressed_tiff_normal_roundtrip(self):
        out=io.BytesIO(); Image.new('RGB',(17,23),'blue').save(out,'TIFF',compression='tiff_lzw')
        out.seek(0)
        with Image.open(out) as im:
            im.load(); self.assertEqual(im.size,(17,23))
if __name__=='__main__': unittest.main(verbosity=2)
