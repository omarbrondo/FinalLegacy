"""Videos de presentación (logo de la empresa e intro del juego) antes del título.
Los MP4 van en la carpeta 'videos/' junto a retro_legacy.py. Se saltan con clic, ESPACIO, ENTER, ESC o un botón del mando.
Necesita ffmpeg: viene con `pip install imageio-ffmpeg` (o el ffmpeg del sistema). Si falta algo, el juego arranca igual sin los videos."""
import os
import shutil
import subprocess
import sys
import tempfile
import pygame
from .common import H, W

SPLASH_VIDEOS = ('logo.mp4', 'intro.mp4')        # en orden de reproducción
VIDEO_FPS = 30
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _videos_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), 'videos')


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which('ffmpeg')


def _skip_event(e):
    return e.type in (pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN) or (
        e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER))


def play_video(game, path, ff):
    """Reproduce un MP4 a pantalla completa (con barras si el formato no coincide). Devuelve False si el usuario cerró la ventana."""
    tmp = None
    snd = None
    chan = None
    proc = None
    try:
        if pygame.mixer.get_init():
            fd, tmp = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            r = subprocess.run([ff, '-v', 'error', '-y', '-i', path, '-vn', '-ac', '2', '-ar', '44100', '-f', 'wav', tmp],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)
            if r.returncode == 0 and os.path.getsize(tmp) > 1000:
                snd = pygame.mixer.Sound(tmp)
        vf = 'scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black' % (W, H, W, H)
        proc = subprocess.Popen([ff, '-v', 'error', '-i', path, '-an', '-vf', vf, '-r', str(VIDEO_FPS), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)
        size = W * H * 3
        pygame.mouse.set_visible(False)
        if snd is not None:
            chan = pygame.mixer.find_channel(True)
            chan.play(snd)
        clock = pygame.time.Clock()
        start = pygame.time.get_ticks()
        idx = 0
        frame = None
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return False
                if _skip_event(e):
                    return True
            want = int((pygame.time.get_ticks() - start) / 1000.0 * VIDEO_FPS)
            while idx <= want:                       # si va atrasado, descarta cuadros para no perder el sincronismo con el audio
                buf = proc.stdout.read(size)
                if len(buf) < size:
                    return True
                frame = buf
                idx += 1
            if frame is not None:
                game.screen.blit(pygame.image.frombuffer(frame, (W, H), 'RGB'), (0, 0))
                pygame.display.flip()
            clock.tick(VIDEO_FPS * 2)
    finally:
        if chan is not None:
            chan.stop()
        if proc is not None:
            try:
                proc.kill()
                proc.stdout.close()
            except Exception:
                pass
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
        pygame.mouse.set_visible(True)


def play_splashes(game):
    """Logo e intro antes del título. Nunca debe impedir que arranque el juego."""
    try:
        d = _videos_dir()
        files = [os.path.join(d, n) for n in SPLASH_VIDEOS if os.path.isfile(os.path.join(d, n))]
        ff = _ffmpeg() if files else None
        if not files or not ff:
            return
        game.audio.music(None)
        for f in files:
            game.screen.fill((0, 0, 0))
            pygame.display.flip()
            if not play_video(game, f, ff):
                pygame.quit()
                sys.exit()
        pygame.event.clear()
        game.go('title')
    except Exception as ex:                    # cualquier falla de video: seguir sin él
        print('Video de presentación omitido:', ex)
        try:
            game.go('title')
        except Exception:
            pass
