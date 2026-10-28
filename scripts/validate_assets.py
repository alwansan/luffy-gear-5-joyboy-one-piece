"""Validate checked-in media and an optional downloaded PNG archive."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, help='Path to frames.zip downloaded from Releases')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'assets/manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if digest(ROOT / name) != expected:
            raise SystemExit(f'Checksum mismatch: {name}')
    assert len(list((ROOT / 'assets/keyframes').glob('key_*.png'))) == 8
    for name, size in [('animation.mp4', (1024, 1024)), ('phone.mp4', (1080, 1920))]:
        result = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_frames,duration', '-of', 'json',
            str(ROOT / 'assets' / name)])
        stream = json.loads(result)['streams'][0]
        assert (stream['width'], stream['height']) == size, name
        assert stream['r_frame_rate'] == '30/1', name
        assert int(stream['nb_frames']) == 300 and abs(float(stream['duration']) - 10) < .001, name
    with Image.open(ROOT / 'assets/animation.gif') as gif:
        assert gif.size == (640, 640) and gif.n_frames == 300 and gif.info.get('loop') == 0
        total = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            total += gif.info['duration']
        assert total == 10000, total
    if args.frames:
        assert digest(args.frames) == manifest['frames_release']['sha256'], 'Archive checksum mismatch'
        with zipfile.ZipFile(args.frames) as archive:
            assert archive.testzip() is None
            expected_names = [f'frame_{i:03}.png' for i in range(300)]
            assert sorted(archive.namelist()) == expected_names
            ends = []
            for i, name in enumerate(expected_names):
                with Image.open(io.BytesIO(archive.read(name))) as image:
                    assert image.size == (1024, 1024), name
                    if i in (0, 299):
                        ends.append(image.convert('RGB').tobytes())
            assert ends[0] == ends[1], 'Loop endpoints differ'
        print('Release archive: 300 PNG frames, checksums and loop endpoints verified.')
    else:
        print('Archive not checked. Download frames.zip from Releases and pass --frames PATH.')
    print('Media checksums, video specifications, GIF timing and key drawings verified.')

if __name__ == '__main__':
    main()
