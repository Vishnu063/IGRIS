"""Fixed offline headless Handy invocation. No mic/clipboard/keyboard API."""
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile


def main():
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
    home=Path('/tmp/handy-home');home.mkdir()
    data=Path('/tmp/handy-data/com.pais.handy');data.mkdir(parents=True)
    (data/'models').symlink_to('/models',target_is_directory=True)
    env={'PATH':'/usr/bin:/bin','HOME':str(home),'XDG_DATA_HOME':'/tmp/handy-data','XDG_CONFIG_HOME':'/tmp/handy-config',
         'XDG_CACHE_HOME':'/tmp/handy-cache','DISPLAY':':99','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2',
         'NO_PROXY':'127.0.0.1,localhost'}
    display=subprocess.Popen(['/usr/bin/Xvfb',':99','-screen','0','640x480x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
    try:
        import time
        for _ in range(100):
            if Path('/tmp/.X11-unix/X99').exists():break
            if display.poll() is not None:raise RuntimeError('Private virtual display unavailable.')
            time.sleep(.02)
        help_result=subprocess.run(['/usr/bin/handy','--help'],capture_output=True,text=True,env=env,timeout=10,check=True)
        if '--transcribe-file' not in help_result.stdout or '--json' not in help_result.stdout:raise ValueError('Verified public headless CLI unavailable.')
        with tempfile.TemporaryFile() as output:
            result=subprocess.run(['/usr/bin/handy','--transcribe-file','/input/audio.wav','--model','small','--json'],
                stdout=output,stderr=subprocess.DEVNULL,env=env,timeout=150)
            if result.returncode:raise RuntimeError('Handy headless transcription failed.')
            output.seek(0);raw=output.read(65537)
        if len(raw)>65536:raise ValueError('Unexpected transcription output volume.')
        result=json.loads(raw)
        print(json.dumps({'schema_version':1,'model':result['model'],'text':result['text'],
              'audio_secs':result['audio_secs'],'load_ms':result['load_ms'],'transcribe_ms':result['transcribe_ms']}),flush=True)
    finally:
        display.terminate()
        try:display.wait(timeout=3)
        except subprocess.TimeoutExpired:display.kill();display.wait(timeout=3)


if __name__=='__main__':main()
