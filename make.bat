@echo off

call %USERPROFILE%\redenv\Scripts\activate.bat
if [%1] == [] goto help

REM This allows us to expand variables at execution
setlocal ENABLEDELAYEDEXPANSION

goto %1

:reformat
isort .
black .
exit /B %ERRORLEVEL%

:isort
isort .
exit /B %ERRORLEVEL%

:black
black .
exit /B %ERRORLEVEL%

:stylediff
isort --atomic --check --diff --line-length 99 --use-parentheses .
black --check --diff -l 99 .
exit /B %ERRORLEVEL%

:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Reformat all .py files being tracked by git.
echo   isort                      Reformat all .py files only with isort.
echo   black                      Reformat all .py files only with black.
echo   stylediff                  Check .py files for style diffs.