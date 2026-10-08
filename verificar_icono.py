"""Comprueba si un .exe lleva un ícono incrustado.  Uso:  python verificar_icono.py [ruta.exe]
(por defecto dist\\RetroLegacy\\RetroLegacy.exe). Necesita pefile, que PyInstaller instala en Windows."""
import os
import struct
import sys

try:
    import pefile
except ImportError:
    print('Falta pefile: pip install pefile')
    sys.exit(2)

RT_ICON, RT_GROUP_ICON = 3, 14
ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join('dist', 'RetroLegacy', 'RetroLegacy.exe')
if not os.path.isfile(ruta):
    print('No existe', ruta)
    sys.exit(2)

ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icono', 'retro_legacy.ico')
nuestros = set()
if os.path.isfile(ico):
    d = open(ico, 'rb').read()
    for i in range(struct.unpack('<H', d[4:6])[0]):
        sz, off = struct.unpack('<II', d[6 + 16 * i + 8:6 + 16 * i + 16])
        nuestros.add(d[off:off + sz])

pe = pefile.PE(ruta, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
total = coinciden = grupos = 0
if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
    for ent in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if ent.id == RT_GROUP_ICON:
            grupos = sum(len(sub.directory.entries) for sub in ent.directory.entries)
        if ent.id == RT_ICON:
            for sub in ent.directory.entries:
                for leaf in sub.directory.entries:
                    r = leaf.data.struct
                    blob = pe.get_data(r.OffsetToData, r.Size)
                    total += 1
                    coinciden += blob in nuestros
print('Ruta:', ruta)
print('Grupos de ícono: %d | imágenes de ícono: %d | iguales a icono/retro_legacy.ico: %d' % (grupos, total, coinciden))
if coinciden:
    print('RESULTADO: el .exe lleva el ícono del juego incrustado. Si el Explorador no lo muestra, es la caché de íconos de Windows.')
elif total:
    print('RESULTADO: el .exe tiene un ícono, pero NO es el del juego (probablemente el predeterminado de PyInstaller).')
else:
    print('RESULTADO: el .exe no tiene ícono incrustado.')
