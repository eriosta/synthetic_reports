@echo off
REM Windows batch script for running multiple SynthRad configurations
REM Usage: run_multiple_configs.bat [config_file] [--parallel] [--workers N]

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: run_multiple_configs.bat [config_file] [--parallel] [--workers N]
    echo.
    echo Examples:
    echo   run_multiple_configs.bat sample_configs.json
    echo   run_multiple_configs.bat my_configs.json --parallel --workers 4
    echo.
    echo To create a sample config file first:
    echo   python scripts/multi_config_generator.py --create-sample
    exit /b 1
)

set CONFIG_FILE=%1
set PARALLEL=false
set MAX_WORKERS=

:parse_args
shift
if "%1"=="" goto :run
if "%1"=="--parallel" (
    set PARALLEL=true
    goto :parse_args
)
if "%1"=="--workers" (
    shift
    set MAX_WORKERS=%1
    goto :parse_args
)
goto :parse_args

:run
echo Running multiple SynthRad configurations...
echo Config file: %CONFIG_FILE%
echo Parallel: %PARALLEL%
if not "%MAX_WORKERS%"=="" echo Max workers: %MAX_WORKERS%
echo.

if "%PARALLEL%"=="true" (
    if "%MAX_WORKERS%"=="" (
        python scripts/multi_config_generator.py --configs %CONFIG_FILE% --parallel
    ) else (
        python scripts/multi_config_generator.py --configs %CONFIG_FILE% --parallel --max-workers %MAX_WORKERS%
    )
) else (
    python scripts/multi_config_generator.py --configs %CONFIG_FILE%
)

echo.
echo Done! Check the output directories for generated reports.
pause
