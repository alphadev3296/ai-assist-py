@echo off
REM Linting script for Windows

echo Running code quality checks...
python lint.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo All checks passed!
    exit /b 0
) else (
    echo.
    echo Some checks failed!
    exit /b 1
)
