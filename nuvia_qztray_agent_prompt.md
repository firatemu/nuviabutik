# AI Agent Prompt — Nuvia Butik QZ Tray Print Integration

---

## ROLE & CONTEXT

You are a senior full-stack developer working on **Nuvia Butik**, a Django-based retail management system deployed on a remote server. Your task is to migrate the existing label printing system from a custom WebSocket print agent to **QZ Tray** — a professionally signed, cross-platform local print bridge.

The system prints product labels in **ZPL (Zebra Programming Language)** format to an **Xprinter XP-470B** thermal label printer (56mm × 40mm, 8 dots/mm) connected via USB to the user's local machine.

---

## CURRENT ARCHITECTURE (What exists today)

### Backend (Django — Remote Server)
- **Endpoint:** `POST /urun/api/etiket/websocket/<variant_id>/`
- Fetches product/variant data from the database
- Generates ZPL string via `stoktakip/advanced_zpl.py` (Python class)
- Returns JSON: `{ "zpl_data": "^XA...^XZ", "success": true }`
- Secondary endpoint: `GET /urun/api/getlabel/` — downloads `.prn` file for testing

### Frontend (Browser)
- `nuvia-print-manager.js` — orchestrates print requests, calls Django API
- `nuvia-bridge.js` — manages WebSocket connection to `ws://localhost:9876`
- Current flow: Button click → Django API (get ZPL) → WebSocket to local agent → Printer
- HTTP fallback: `http://localhost:9876/print` if WebSocket fails
- Port scanning: tries ports 9876–9880 if default fails

### Local Agent (OLD — to be replaced)
- Installed via `NuviaButikPrintAgent-Installer.bat`
- Windows-only service listening on `ws://localhost:9876`
- Receives `{ type: 'print_label', zpl_data: "..." }` and sends RAW to printer

### Label Templates
- **Static:** `stoktakip/advanced_zpl.py` — hardcoded ZPL generator
- **Dynamic:** `EtiketSablonu` + `EtiketSablonEleman` Django models with drag-and-drop designer
- **Printer settings:** `YaziciAyarlari` model (copies, width, height per user)

---

## YOUR TASK — Complete QZ Tray Migration

Replace `nuvia-bridge.js` and update `nuvia-print-manager.js` to use **QZ Tray** instead of the custom WebSocket agent. QZ Tray is already installed on the client machine.

### Files to create / modify:

#### 1. `nuvia-bridge.js` — Full replacement
Rewrite this file entirely using the QZ Tray JavaScript API (`qz-tray.js`). Requirements:

- Import/load `qz-tray.js` (assume it is available at `/static/js/qz-tray.js`)
- On page load, attempt `qz.websocket.connect()` with automatic retry (exponential backoff, max 5 retries, starting at 1s)
- Handle QZ Tray certificate/signature: use **unsigned mode** for development (`qz.security.setCertificatePromise` + `qz.security.setSignatureAlgorithm` set to bypass) with a clear `TODO` comment for production signing
- Expose a clean async function: `NuviaBridge.print(zplString, printerName)` — returns a Promise
- Expose `NuviaBridge.getStatus()` — returns `'connected'`, `'connecting'`, or `'disconnected'`
- Expose `NuviaBridge.listPrinters()` — returns array of available printer names
- Dispatch a custom DOM event `nuvia:printer-status` with `{ detail: { status, message } }` on every connection state change
- On disconnect, attempt reconnect every 5 seconds silently

#### 2. `nuvia-print-manager.js` — Update bridge calls only
Keep all existing Django API call logic intact. Only replace the bridge communication parts:

- Replace all `ws.send(...)` and WebSocket logic with `await NuviaBridge.print(zplData, printerName)`
- Read printer name from `YaziciAyarlari` if available, otherwise use `qz.printers.getDefault()`
- Keep the existing single-print and bulk-print (`Toplu Yazdır`) flows
- Add proper `try/catch` around every print call with user-facing error messages in Turkish
- After successful print, optionally call `POST /urun/api/print-log/` if that endpoint exists

#### 3. `etiket_status_widget.html` (new — Django template snippet)
A small reusable HTML+JS snippet to include in any Django template that has a print button. Shows real-time printer connection status:

- Listen for `nuvia:printer-status` DOM event
- Display a small status badge: 🟢 **Yazıcı Bağlı** / 🔴 **QZ Tray Bağlı Değil** / 🟡 **Bağlanıyor...**
- If disconnected, show actionable message: *"QZ Tray uygulamasını başlatın"*
- No external CSS dependencies — use inline styles compatible with Bootstrap 4/5

---

## CONSTRAINTS & REQUIREMENTS

### Code Quality
- All JavaScript must be **ES2020+**, no jQuery dependency
- Use `async/await` throughout, no raw Promise chains
- Add JSDoc comments to all exported functions
- Handle all QZ Tray error codes gracefully (connection refused, printer not found, print failed)

### QZ Tray Specifics
- Print config: `qz.configs.create(printerName, { raw: true })` for ZPL/RAW mode
- Print data: `[{ type: 'raw', format: 'plain', data: zplString }]`
- Always call `qz.websocket.disconnect()` on `window.beforeunload`
- Default QZ Tray WebSocket port is `8181` (not 9876 — this is different from the old agent)
- QZ Tray connects via `wss://localhost:8181` (secure) or `ws://localhost:8181`

### Django Backend (do NOT change)
- Do not modify any Django views, models, or URLs
- Do not change the ZPL generation logic in `advanced_zpl.py`
- The API response format `{ "zpl_data": "...", "success": true }` stays as-is

### Error Messages (Turkish)
All user-facing errors must be in Turkish:
- Connection failed → `"QZ Tray bağlantısı kurulamadı. Lütfen QZ Tray uygulamasının çalıştığından emin olun."`
- Printer not found → `"Yazıcı bulunamadı. Lütfen yazıcı bağlantısını kontrol edin."`
- Print failed → `"Yazdırma işlemi başarısız oldu: {error}"`
- Success → `"Etiket başarıyla gönderildi."`

---

## EXPECTED OUTPUT

Provide the following, in this order:

1. **`nuvia-bridge.js`** — complete rewrite (QZ Tray integration)
2. **`nuvia-print-manager.js`** — only the changed sections, with `// ... existing code ...` placeholders for unchanged parts
3. **`etiket_status_widget.html`** — the status badge snippet
4. **`INTEGRATION_NOTES.md`** — short markdown file covering:
   - How to load `qz-tray.js` in Django templates (static file setup)
   - The one-time QZ Tray certificate setup step for production
   - How to test the integration without a physical printer (QZ Tray printer simulator)
   - Any breaking changes vs the old agent

---

## ADDITIONAL CONTEXT

- Django version: assume 4.x, using class-based views
- Frontend: vanilla JS + Bootstrap 4, no React/Vue
- The `YaziciAyarlari` model has fields: `yazici_adi` (printer name string), `kopya_sayisi` (int), `genislik` (int, mm), `yukseklik` (int, mm)
- Bulk print (`Toplu Yazdır`) sends multiple ZPL strings sequentially — maintain this behavior with QZ Tray, adding a 300ms delay between prints to avoid buffer overflow
- The system may be used by non-technical staff — error messages and status indicators must be extremely clear
