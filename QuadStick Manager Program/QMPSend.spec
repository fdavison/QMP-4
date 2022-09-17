# -*- mode: python -*-

block_cipher = None


a = Analysis(['QMPSend.py'],
             pathex=['D:\\Users\\fdavison\\Documents\\GitHub\\QMP\\QuadStick Manager Program'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
a.datas += [('quadstickx.ico', 'quadstickx.ico', 'DATA')]
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='QMPSend',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='quadstickx.ico')
