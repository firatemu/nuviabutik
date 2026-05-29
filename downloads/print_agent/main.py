import os
import sys

# Fix for Uvicorn crashing in PyInstaller --noconsole mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import base64
import tempfile
import uvicorn
from contextlib import asynccontextmanager

from utils.logger import logger, config
from utils.security import verify_token, check_origin, ALLOWED_ORIGINS
from services.print_service import PrintService

# Initialize printer service
printer_service = PrintService(
    default_printer=config['printer']['default_name'],
    fallback=config['printer']['fallback_to_default']
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Nuvia Print Agent...")
    yield
    logger.info("Shutting down Nuvia Print Agent...")

from starlette.middleware.base import BaseHTTPMiddleware

class PrivateNetworkMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.headers.get("access-control-request-private-network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

app = FastAPI(title="Nuvia Print Agent", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrivateNetworkMiddleware)

class PrintRequest(BaseModel):
    format: str # 'tspl', 'raw', 'pdf'
    data: str # Base64 encoded string or raw string
    printer: Optional[str] = None
    is_base64: Optional[bool] = False

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/printers", dependencies=[Depends(verify_token)])
def list_printers(request: Request, _: bool = Depends(check_origin)):
    """List all available Windows printers."""
    return {"success": True, "printers": printer_service.get_printers()}

@app.get("/status", dependencies=[Depends(verify_token)])
def get_status(request: Request, _: bool = Depends(check_origin)):
    """Get the current target printer status."""
    target = printer_service.get_target_printer()
    return {
        "success": True,
        "target_printer": target,
        "agent_status": "running"
    }

@app.post("/print", dependencies=[Depends(verify_token)])
def print_label(request: Request, print_req: PrintRequest, _: bool = Depends(check_origin)):
    try:
        data_bytes = None
        
        if print_req.is_base64 or print_req.format == 'pdf':
            data_bytes = base64.b64decode(print_req.data)
        else:
            # Handle Windows encoding for TSPL (CRLF might be required)
            # If plain string TSPL/ZPL, ensure CRLF and encode
            raw_str = print_req.data.replace('\r\n', '\n').replace('\n', '\r\n')
            data_bytes = raw_str.encode('windows-1254', errors='ignore')

        if print_req.format in ['tspl', 'raw', 'zpl']:
            printer_service.print_raw(data_bytes, print_req.printer)
            
        elif print_req.format == 'pdf':
            # For PDF, sending raw bytes to a TSPL printer usually fails.
            # Best practice: save to temp file and use SumatraPDF or Ghostscript
            # Here we provide a simplified stub that assumes the driver can handle it via RAW,
            # or for real production, call SumatraPDF CLI.
            logger.warning("PDF printing requires appropriate print drivers or external viewer (SumatraPDF/Ghostscript) in production Windows.")
            
            # Simple fallback: send to driver (only works if driver renders PDFs natively, rare)
            # A full implementation would use pdf2image -> win32print GDI drawing
            printer_service.print_raw(data_bytes, print_req.printer)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        return {"success": True, "message": "Job sent to printer"}

    except Exception as e:
        logger.error(f"Print error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    host = config['server']['host']
    port = config['server']['port']
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
