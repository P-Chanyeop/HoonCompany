@echo off
echo === SOFTCAT 네이버 카페 자동화 빌드 ===
pyinstaller --noconfirm --onefile --windowed ^
    --name "SOFTCAT_카페자동화" ^
    --icon "softcat2.ico" ^
    --add-data "softcat2.ico;." ^
    --add-data "config.ini;." ^
    --hidden-import "google.auth.transport.requests" ^
    --hidden-import "google.oauth2.credentials" ^
    --hidden-import "google_auth_oauthlib.flow" ^
    --hidden-import "googleapiclient.discovery" ^
    --hidden-import "PIL" ^
    "네이버카페글쓰기.py"
echo === 빌드 완료 ===
echo 결과: dist\SOFTCAT_카페자동화.exe
pause
