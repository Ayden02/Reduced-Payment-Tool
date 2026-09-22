@echo off
setlocal

echo Installing/updating build dependency...
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

echo.
echo Building ProviderPaymentAllocator.exe...
python -m PyInstaller --clean --noconfirm --onefile --windowed --name ProviderPaymentAllocator provider_payment_allocator.py
if errorlevel 1 goto :error

echo.
echo Build complete.
echo Executable: dist\ProviderPaymentAllocator.exe
pause
exit /b 0

:error
echo.
echo Build failed. Review the messages above.
pause
exit /b 1
