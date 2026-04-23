@echo off

call %USERPROFILE%\redenv\Scripts\activate.bat
if [%1] == [] goto help

REM This allows us to expand variables at execution
setlocal ENABLEDELAYEDEXPANSION

goto %1

:reformat
ruff format .
if errorlevel 1 exit /B %ERRORLEVEL%
ruff check . --fix --unsafe-fixes
exit /B %ERRORLEVEL%

:black
ruff format .
exit /B %ERRORLEVEL%

:isort
ruff check . --select I --fix
exit /B %ERRORLEVEL%

:stylediff
ruff check .
if errorlevel 1 exit /B %ERRORLEVEL%
ruff format . --check
exit /B %ERRORLEVEL%

:crowdin
redgettext . --command-docstrings --omit-empty --recursive --verbose --include-context --exclude-files "**/AAA3A_utils/*"
exit /B %ERRORLEVEL%

:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Apply Ruff fixes + format all .py files.
echo   black                      Format all .py files via Ruff.
echo   isort                      Sort imports via Ruff (rule I).
echo   stylediff                  Check lint + formatting without modifying files.
echo   crowdin                    Create translations source files.