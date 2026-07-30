@echo off
setlocal
set "DIR=%LOCALAPPDATA%\SupportBotPresence"
mkdir "%DIR%" 2>nul
copy /Y "%~dp0supportbot-presence.exe" "%DIR%\supportbot-presence.exe" >nul
schtasks /Create /F /SC ONLOGON /RL LIMITED /TN "SupportBot Presence" /TR "\"%DIR%\supportbot-presence.exe\"" >nul
start "" "%DIR%\supportbot-presence.exe"
echo SupportBot Presence installed. Return to the browser.
pause
