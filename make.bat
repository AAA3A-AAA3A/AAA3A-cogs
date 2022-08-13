@echo off

if [%1] == [] goto help

if exist "%~dp0.venv\" (
    set "VENV_PYTHON=%~dp0.venv\Scripts\python"
) else (
    set VENV_PYTHON=python
)

goto %1

:reformat
"%VENV_PYTHON%" -m isort "%~dp0." -m 7 -l 1000 -p redbot -s "cogsutils.py" --sg ".github/* --sg "docs/*" --sp "%~dp0.\.isort.cfg"
goto:eof

:stylecheck
"%VENV_PYTHON%" -m isort --check "%~dp0."
goto:eof

:stylediff
"%VENV_PYTHON%" -m isort --check --diff "%~dp0."
goto:eof

:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Reformat all .py files being tracked by git.
echo   stylecheck                 Check which tracked .py files need reformatting.
echo   stylediff                  Show the post-reformat diff of the tracked .py files
echo                              without modifying them.