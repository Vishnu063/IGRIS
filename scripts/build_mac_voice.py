"""Explicit native helper compilation; no microphone, model download or service."""
import hashlib,json,os,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise SystemExit('BLOCKED: actual Apple Silicon macOS required.')
    if sys.argv[1:]!=['--allow-changes']:raise SystemExit('Explicit --allow-changes required for local compilation/ad-hoc signing.')
    if subprocess.run(['/usr/bin/xcode-select','--print-path'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode:
        raise SystemExit('BLOCKED: Apple Command Line Tools/Swift SDK unavailable. No toolchain download was started; review installation separately.')
    root=ROOT/'runtime/native-voice';root.mkdir(mode=0o700,parents=True,exist_ok=True)
    app=root/'IGRIS Manual Voice.app';app.mkdir(mode=0o700);contents=app/'Contents';binary=contents/'MacOS/igris-voice';binary.parent.mkdir(parents=True,mode=0o700)
    import shutil
    shutil.copyfile(ROOT/'packaging/macos/Voice-Info.plist',contents/'Info.plist')
    subprocess.run(['/usr/bin/xcrun','swiftc','-swift-version','5','-O','-target','arm64-apple-macosx13.0',str(ROOT/'packaging/macos/native_voice.swift'),'-o',str(binary)],check=True,timeout=180)
    subprocess.run(['/usr/bin/codesign','--sign','-','--identifier','local.igris.manualvoice',str(app)],check=True,timeout=30)
    subprocess.run(['/usr/bin/codesign','--verify','--strict',str(app)],check=True,timeout=30)
    manifest={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'packaging/macos/native_voice.swift').read_bytes()).hexdigest(),'plist_sha256':hashlib.sha256((contents/'Info.plist').read_bytes()).hexdigest(),'compiled_on':platform.platform(),'verified_human_voice':False}
    (root/'build.json').write_text(json.dumps(manifest,indent=2)+'\n');(root/'build.json').chmod(0o600)
    print('Native helper built; no microphone or playback started. Human/permission/language acceptance still required.')
if __name__=='__main__':main()
