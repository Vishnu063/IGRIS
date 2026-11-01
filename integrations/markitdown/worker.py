"""Single local conversion, explicit converter set, offline and without plugins."""
import contextlib,io,json,logging,os,resource,socket,sys,time
os.environ.clear();os.environ.update(HOME='/tmp',PATH='/usr/bin:/bin',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(45,45));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,)*2)
sys.path.insert(0,'/opt/igris/packages');logging.disable(logging.CRITICAL)
from markitdown import MarkItDown
from markitdown.converters import PdfConverter,DocxConverter,XlsxConverter,PptxConverter,HtmlConverter
from pathlib import Path
started=time.monotonic();packet=json.loads(sys.stdin.buffer.read(1025));suffix=packet['suffix']
classes={'.pdf':PdfConverter,'.docx':DocxConverter,'.xlsx':XlsxConverter,'.pptx':PptxConverter,'.html':HtmlConverter}
if set(packet)!={'suffix'} or suffix not in classes or os.getuid()==0:raise ValueError('Invalid conversion profile.')
try:socket.create_connection(('192.0.2.1',9),timeout=.1)
except OSError as error:
 if error.errno!=101:raise
else:raise RuntimeError('Network unavailable requirement failed.')
class OfflineRequests:
 def get(self,*args,**kwargs):raise PermissionError('Remote conversion disabled.')
 def post(self,*args,**kwargs):raise PermissionError('Remote conversion disabled.')
with contextlib.redirect_stdout(io.StringIO()):
 converter=MarkItDown(enable_builtins=False,enable_plugins=False,requests_session=OfflineRequests());converter.register_converter(classes[suffix]())
 result=converter.convert_local('/input/document'+suffix)
 text=result.text_content
raw=text.encode('utf-8');bounded=raw[:6000].decode('utf-8',errors='ignore')
print(json.dumps({'origin':'real_markitdown','format':suffix,'markdown':bounded,'truncated':len(raw)>6000,'source_markdown_bytes':len(raw),'network_denied':True,'seconds':round(time.monotonic()-started,3),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
