# Provider Payment Allocator

A small desktop calculator for allocating a reduced provider-payment total in proportion to providers' original charges.

## What it does

1. Enter each provider and its original charge.
2. At startup, indicate whether any provider is exempt from reduction.
3. Exempt providers receive their full original charge.
4. Their payments are subtracted from the reduced total.
5. The remaining amount is distributed proportionally among the non-exempt providers based on their original charges.
6. Results can be exported to CSV.

The program uses exact cent-based allocation so the displayed provider payments add up exactly to the entered reduced total.

## For firm employees

The intended employee-facing version is the Windows executable:

`ProviderPaymentAllocator.exe`

Employees should be able to double-click the executable. They do **not** need Python installed.

For internal distribution, place the approved executable in a shared firm location such as a network drive, SharePoint, OneDrive, or your firm's software deployment system.

## Running the source code

Python 3 is required.

```bash
python provider_payment_allocator.py
```

On systems where the command is `python3`:

```bash
python3 provider_payment_allocator.py
```

The application itself uses only Python's standard library.

## Building the Windows executable

PyInstaller is a development/build dependency only.

Install it:

```bash
python -m pip install -r requirements-dev.txt
```

Then build:

```bash
pyinstaller --clean --noconfirm --onefile --windowed --name ProviderPaymentAllocator provider_payment_allocator.py
```

Or, on Windows, double-click/run:

```text
build_windows.bat
```

The finished executable will be:

```text
dist\ProviderPaymentAllocator.exe
```

### Important

Build the Windows executable on Windows. PyInstaller is not a cross-compiler, so a macOS build does not produce a Windows `.exe`.

## Suggested GitHub workflow

Keep the source code in the repository and distribute compiled executables through **GitHub Releases** rather than committing `.exe` files directly into the source tree.

A GitHub Actions workflow is included at:

`.github/workflows/build-windows.yml`

You can run it manually from the repository's **Actions** tab. It builds the Windows executable and stores it as a downloadable workflow artifact.

For an employee-ready release:

1. Test the generated `.exe` on a clean Windows computer.
2. In GitHub, open **Releases**.
3. Create a release such as `v1.0.0`.
4. Attach the tested `ProviderPaymentAllocator.exe`.
5. Give firm employees the approved internal copy or release file.

## Repository structure

```text
provider-payment-allocator/
├── provider_payment_allocator.py
├── build_windows.bat
├── requirements-dev.txt
├── README.md
├── .gitignore
└── .github/
    └── workflows/
        └── build-windows.yml
```

## Privacy

The calculator does not require patient names or patient identifiers and does not send entered data anywhere. Calculations occur locally on the computer.

For a law-firm deployment, avoid adding patient PHI/PII unless the firm's security and compliance requirements have been reviewed.

## Disclaimer

This software is a calculation aid. Users should independently verify payment figures and apply the firm's legal, contractual, and accounting requirements before issuing payments.
