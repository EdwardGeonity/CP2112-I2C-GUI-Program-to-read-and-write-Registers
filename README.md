# CP2112

![app](https://github.com/user-attachments/assets/68bf2ced-5740-437a-93e6-8933c99d89a6)

CP2112 I²C Control Tool

A Python GUI application for communicating with I²C devices using the Silicon Labs CP2112 HID-to-I²C bridge.
Supports register read/write operations and execution of command scripts.
✨ Features

    ✅ Read/write to 16-bit I²C registers (1 to 32 bytes)

    ✅ Execute custom scripts with WBlock syntax

    ✅ Batch processing via Sequence all mode

    ✅ GUI-based input for slave address (HEX/BIN), register and data

    ✅ Multi-byte read and write support

    ✅ Real-time CP2112 communication via HID

    ✅ Optional debug logging (--debug)

📜 Script Format Example

Addr=2D

WBlock(01, MyInit) = [
    (0103, 01, 1),     # Reset
    (0104, 0123, 2),   # Set mode
]

    Addr — target I²C slave address (hex)

    WBlock(ID, Name) — script block with name and ID

    Each tuple: (Register, Data, Length)

    Use Sequence all to execute all blocks in order

🚀 How to Run
On macOS / Linux / Windows:

python CP2112_SimpleProg_debug_mode.py

With debug logs:

python CP2112_SimpleProg_debug_mode.py --debug

🛠 Building App / EXE

    macOS:

pyinstaller --windowed --name "CP2112_GUI" CP2112_SimpleProg_debug_mode.py

    Windows:

pyinstaller --windowed --name "CP2112_GUI.exe" CP2112_SimpleProg_debug_mode.py
