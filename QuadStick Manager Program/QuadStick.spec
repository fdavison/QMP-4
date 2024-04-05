# -*- mode: python -*-
import os

block_cipher = None


def get_locales_data():
    locales_data = []
    for locale in os.listdir(os.path.join('./locales')):
        if not locale.endswith('.pot') and not locale.endswith('.txt'):
            locales_data.append((
                os.path.join('./locales', locale, 'LC_MESSAGES/*.mo'),
                os.path.join('locales', locale, 'LC_MESSAGES')
            ))
    return locales_data


a = Analysis(['QuadStick.py'],
             pathex=['D:\\Users\\fdavison\\Documents\\GitHub\\QMP-4\\QuadStick Manager Program'],
             binaries=None,
             datas=get_locales_data(),
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
a.datas += [('ViGEmClient.dll', 'ViGEmClient.dll', 'DATA')]
a.datas += [('quadstickx.ico', 'quadstickx.ico', 'DATA')]
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='QuadStick',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='quadstickx.ico')
