echo Launch SafeNet and plug in SafeNet key, copy password "D4nY3bbw17uwS1,9" to clipboard
pause
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool" sign /tr http://timestamp.sectigo.com /td sha256 /fd sha256 /a "dist\QuadStick.exe"
pause
