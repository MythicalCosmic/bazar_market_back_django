@echo off
echo ========================================
echo   Building Bazar Market Print Agent
echo ========================================
echo.

pip install pyinstaller websockets python-escpos pyusb pillow pywin32
echo.

pyinstaller agent.spec --clean
echo.

if exist "dist\BazarMarketPrinter.exe" (
    echo ========================================
    echo   Build successful!
    echo   Output: dist\BazarMarketPrinter.exe
    echo ========================================
) else (
    echo Build failed. Check errors above.
)
echo.
pause
