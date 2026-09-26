# Keyboard Effects Studio

Keyboard Effects Studio is a Windows desktop app for changing keyboard backlighting on compatible Clevo systems that expose the Insyde DCHU keyboard controller. It provides six animated effects and lets you choose colors, speed, and brightness.

> **Compatibility:** This project currently targets a Clevo single-zone RGB keyboard through `InsydeDCHU.dll`. It is not a universal RGB utility, does not provide per-key lighting, and may not work with every Clevo model or firmware. Hardware compatibility and output have not been confirmed across a range of devices.

## Features

- Spectrum cycle, breathing, two-color fade, color pulse, random color, and solid color
- Adjustable colors, animation speed, and brightness
- Notification-area behavior to keep an effect running while the window is hidden
- Settings saved beside the application

## Download and run

Download `KeyboardEffectsStudio.exe` from the project’s **Releases** page. This is a beta build. Windows may show a security or reputation prompt because the executable is not signed; only run it if you trust the source of the download.

Close any other keyboard-lighting utility that may be controlling the keyboard, launch the app, and approve its Windows administrator prompt. Select **Connect**, choose an effect, then select **Start effect**. Closing the window hides the app in the notification area. Use the tray icon to reopen it or exit.

Use **Stop animation** to stop sending frames while leaving the last color on, or **Turn keyboard off** to send a black frame. If the controller does not respond, the device or firmware may not be compatible.

## Build from source

Builds require Windows, Python 3.12, and PyInstaller. From the repository folder:

```powershell
python -m pip install pyinstaller
.\build.ps1
```

The script creates `KeyboardEffectsStudio.exe` in the repository folder as a one-file, windowed executable with an administrator manifest. The bundled Python/Tk runtime and controller DLL mean end users do not need Python installed.

## Project files

- `src/keyboard_effects_studio.py` — application source
- `assets/` — application icon artwork
- `vendor/InsydeDCHU.dll` — keyboard controller library used by the app
- `build.ps1` — Windows build script
- `settings.json` — neutral starter preferences, loaded and updated by the app

The app loads `settings.json` from beside the executable and updates it when settings change. If the file is missing or invalid, built-in defaults are used.

## Beta status

This software is provided as an early beta. Test it on compatible hardware and report the device model, keyboard controller, Windows version, and any error message when filing an issue. The project makes no guarantee that a particular device or firmware is supported.
