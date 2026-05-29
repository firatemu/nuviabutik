# Nuvia Print Agent (Windows)

This is a production-ready Local Print Agent designed to run as a Windows Service. It replaces QZ Tray and provides a secure `http://localhost:3210` API for sending TSPL, ZPL, and RAW commands to local barcode printers (like Xprinter XP-470B).

## Requirements
- Windows 10/11
- Python 3.10 through 3.13 (e.g. 3.13.x; enable "Add to PATH" during install)

## 1. Setup & Installation
1. Extract this folder to `C:\PrintAgent`
2. Open **Command Prompt as Administrator** and navigate to the directory:
   ```cmd
   cd C:\PrintAgent
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Configure your printer and security settings in `config.json` if needed. Default token is `NuviaSecretPrintToken2026`.

## 2. Running & Building

### To run locally for testing
```cmd
python main.py
```
*API will run on `http://localhost:3210`*

### To compile to standalone `.exe`
You can compile this entire project into a single robust `.exe` so you don't need Python installed on target machines.
```cmd
pip install pyinstaller
pyinstaller --onefile --name NuviaPrintAgent --hidden-import win32timezone main.py
```
The `.exe` will be generated in the `dist\` folder. You can move this `.exe` and `config.json` anywhere.

### To install as a Windows Service
This will ensure the print agent starts automatically when Windows boots.
```cmd
# Run cmd as Administrator
python install_service.py install
python install_service.py start
```

## 3. Example Usage

### TSPL Raw Print Request
```javascript
const printToken = "NuviaSecretPrintToken2026";
const tsplCommand = `SIZE 56 mm, 40 mm\r\nGAP 2 mm, 0 mm\r\nDIRECTION 1\r\nCLS\r\nTEXT 50,50,"3",0,1,1,"NUVIA"\r\nPRINT 1,1\r\n`;

fetch("http://localhost:3210/print", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${printToken}`
    },
    body: JSON.stringify({
        format: "tspl",
        data: tsplCommand, // Plain text natively supported
        is_base64: false
    })
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error(err));
```

### Checking Printer Status
```javascript
fetch("http://localhost:3210/status", {
    headers: { "Authorization": `Bearer ${printToken}` }
})
.then(res => res.json())
.then(data => console.log(data));
```

## 4. Logs
Logs are automatically saved to `C:\PrintAgent\logs\agent.log`. Check here if you have issues finding the printer or getting 500 errors.
