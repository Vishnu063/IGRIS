"""Bounded transport/process fixtures; no claim of native Mac TLS acceptance."""
import hashlib,importlib.util,io,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('igris_asset_fetch_tests',ROOT/'scripts/fetch_hermes_probe_assets.py')
fetcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(fetcher)
class AssetDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.url='https://example.invalid/pinned.tar.gz';self.payload=b'bounded fixture bytes';self.sha=hashlib.sha256(self.payload).hexdigest()
    def native(self):
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(patch.object(fetcher.platform,'system',return_value='Darwin'));stack.enter_context(patch.object(fetcher.platform,'machine',return_value='arm64'));return stack
    def test_native_system_transport_keeps_checksum_and_does_not_use_python_tls(self):
        def transport(url,maximum,output):output.write(self.payload)
        with self.native(),patch.object(fetcher,'_curl_download',transport),patch.object(fetcher.urllib.request,'urlopen') as python_tls:
            result=fetcher.fetch(self.root,'asset.tar.gz',self.url,self.sha,100,native_macos=True)
            self.assertEqual(result.read_bytes(),self.payload);python_tls.assert_not_called()
    def test_wrong_checksum_never_publishes_or_leaves_temporary_audio_or_assets(self):
        def transport(url,maximum,output):output.write(b'untrusted bytes')
        with self.native(),patch.object(fetcher,'_curl_download',transport):
            with self.assertRaisesRegex(ValueError,'integrity'):fetcher.fetch(self.root,'asset.tar.gz',self.url,self.sha,100,native_macos=True)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_python_https_path_remains_available(self):
        response=io.BytesIO(self.payload);response.url=self.url
        with patch.object(fetcher.urllib.request,'urlopen',return_value=response),patch.object(fetcher,'_curl_download') as native:
            self.assertEqual(fetcher.fetch(self.root,'asset.tar.gz',self.url,self.sha,100).read_bytes(),self.payload);native.assert_not_called()
    def test_invalid_scheme_platform_and_existing_cache_preserved(self):
        credential_url=fetcher.urllib.parse.urlunsplit(('https',':'.join(('user','password'))+'@example.invalid','/a','',''))
        for url in ('http://example.invalid/a',credential_url):
            with self.assertRaises(ValueError):fetcher.fetch(self.root,'asset.tar.gz',url,self.sha,100)
        with patch.object(fetcher.platform,'system',return_value='Linux'):
            with self.assertRaises(ValueError):fetcher.fetch(self.root,'asset.tar.gz',self.url,self.sha,100,native_macos=True)
        cached=self.root/'asset.tar.gz';cached.write_bytes(b'Existing owner file.')
        with self.assertRaises(ValueError):fetcher.fetch(self.root,cached.name,self.url,self.sha,100)
        self.assertEqual(cached.read_bytes(),b'Existing owner file.')
    def fixture_process(self,program,observed):
        real_popen=subprocess.Popen
        def launch(args,**kwargs):
            self.assertEqual(args[:2],['/usr/bin/curl','--disable']);self.assertNotIn('--insecure',args)
            self.assertEqual(args[args.index('--proto')+1],'=https');self.assertEqual(args[args.index('--proto-redir')+1],'=https')
            process=real_popen([sys.executable,'-c',program],**kwargs);observed.append(process);return process
        return launch
    def test_real_fixture_process_oversize_and_tls_failure_are_reaped(self):
        for program,maximum in [("import sys;sys.stdout.buffer.write(b'x'*10000);sys.stdout.flush()",8),("import sys;sys.stdout.buffer.write(b'partial');sys.exit(60)",100)]:
            observed=[]
            with patch.object(fetcher.subprocess,'Popen',self.fixture_process(program,observed)),tempfile.TemporaryFile() as output:
                with self.assertRaises(ValueError):fetcher._curl_download(self.url,maximum,output,timeout=3)
            self.assertEqual(len(observed),1);self.assertIsNotNone(observed[0].poll())
    def test_real_fixture_process_timeout_is_cleaned_up(self):
        for program in ('import time;time.sleep(30)','import os,time;os.close(1);time.sleep(30)'):
            observed=[]
            with patch.object(fetcher.subprocess,'Popen',self.fixture_process(program,observed)),tempfile.TemporaryFile() as output:
                with self.assertRaises(TimeoutError):fetcher._curl_download(self.url,100,output,timeout=.05)
            self.assertIsNotNone(observed[0].poll())
