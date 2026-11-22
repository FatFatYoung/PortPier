# Third-Party Notices

The PortPier project (\"the Project\") is built primarily on the Python standard library. For open-source compliance and transparency, the open-source components involved in the development, build, and runtime of this project are listed below together with their license information.

## 1. Runtime Dependencies

This project has **zero external dependencies** (Zero Dependency).
All core networking, cryptography, and GUI functionality is implemented with the **Python standard library**; no third-party libraries such as `requests`, `aiohttp`, or `numpy` are introduced, keeping the project lightweight, secure, and compliant.

### Python Standard Library
- **Components**: `asyncio`, `os`, `sys`, `json`, `hashlib`, `base64`, `struct`, `threading`, `socket`, `tkinter`, `datetime`, `ctypes`, etc.
- **License**: [Python Software Foundation License (PSF)](https://docs.python.org/3/license.html)
- **Copyright**: Copyright © 2001-2026 Python Software Foundation.

### Tcl/Tk (GUI Framework)
- **Components**: `tkinter` (backed by the system Tcl/Tk libraries)
- **License**: [Tcl/Tk License](https://www.tcl.tk/software/tcltk/license.html)
- **Copyright**: Copyright © 1993-1994 The Regents of the University of California. Copyright © 1994-1996 Sun Microsystems, Inc.

## 2. Build Tools

This project uses PyInstaller for packaging and distribution.

### PyInstaller
- **Purpose**: Packages the Python source code into a single-file executable (.exe)
- **License**: GNU General Public License v2 (GPL-2.0) (with Bootloader Exception)
- **Copyright**: Copyright © 2005-2026 PyInstaller Development Team.
- **Compliance Note**:
    - PyInstaller is licensed under the GPL, but includes a **Bootloader Exception** clause.
    - The clause states that executables produced merely by packaging with PyInstaller are **not** considered derivative works of PyInstaller; therefore the packaged program does not need to be open-sourced and may coexist with the MIT license used by this project.

---

### Project License

The code and assets of this project (PortPier) are licensed under the **MIT License**.

Copyright (c) 2026 FatFatYoung
