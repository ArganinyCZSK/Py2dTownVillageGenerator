@echo off
setlocal
cd /d "%~dp0"
title Map Generator
set "PYCMD="

call :scan 3
if not defined PYCMD call :scan 2

if not defined PYCMD (
    echo.
    echo  Python was not found on this computer.
    echo  Install Python 3 from https://www.python.org/downloads/
    echo  and tick "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

set "PYVER="
set "PYEXE="
for /f "delims=" %%V in ('call %PYCMD% -c "import sys; print(sys.version.split()[0])"') do set "PYVER=%%V"
for /f "delims=" %%P in ('call %PYCMD% -c "import sys; print(sys.executable)"') do set "PYEXE=%%P"
echo.
echo  Using Python %PYVER%
echo  %PYEXE%
echo.

%PYCMD% -c "import sys; exec('import tkinter' if sys.version_info[0] > 2 else 'import Tkinter')" >nul 2>nul
if errorlevel 1 (
    echo  WARNING: Tkinter is missing in this Python, the window cannot open.
    echo  The map will be generated and saved as PNG instead.
    echo.
)

%PYCMD% "%~dp0map_generator.py" %*
if errorlevel 1 pause
exit /b


:scan
set "MIN=%~1"
where py >nul 2>nul && call :try "py -%MIN%"
for %%C in (python python3 python2) do call :trywhere %%C
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do call :trypath "%%~D"
for /d %%D in ("%ProgramFiles%\Python*") do call :trypath "%%~D"
for /d %%D in ("%ProgramFiles(x86)%\Python*") do call :trypath "%%~D"
for /d %%D in ("%SystemDrive%\Python*") do call :trypath "%%~D"
for /d %%D in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%ProgramData%\anaconda3") do call :trypath "%%~D"
exit /b

:trywhere
if defined PYCMD exit /b
where %1 >nul 2>nul || exit /b
call :try "%1"
exit /b

:trypath
if defined PYCMD exit /b
if not exist "%~1\python.exe" exit /b
call :try """%~1\python.exe"""
exit /b

:try
if defined PYCMD exit /b
set "CAND=%~1"
set "CAND=%CAND:""="%"
%CAND% -c "import sys; sys.exit(0 if sys.version_info[0] == %MIN% and sys.version_info >= (2, 6) else 1)" >nul 2>nul
if not errorlevel 1 set "PYCMD=%CAND%"
exit /b
