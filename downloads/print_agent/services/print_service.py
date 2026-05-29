import win32print
import win32con
import os
from typing import List, Optional
from utils.logger import logger

class PrintService:
    def __init__(self, default_printer: str, fallback: bool = True):
        self.default_printer = default_printer
        self.fallback = fallback

    def get_printers(self) -> List[str]:
        """Get a list of all installed printers on the Windows machine."""
        printers = []
        try:
            printer_flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            for printer in win32print.EnumPrinters(printer_flags):
                printers.append(printer[2])
        except Exception as e:
            logger.error(f"Error enumerating printers: {e}")
        return printers

    def get_target_printer(self, requested_printer: Optional[str] = None) -> str:
        """Resolve which printer to use."""
        available_printers = self.get_printers()
        
        target = requested_printer or self.default_printer
        
        if target in available_printers:
            return target
            
        if self.fallback and available_printers:
            default = win32print.GetDefaultPrinter()
            logger.warning(f"Printer '{target}' not found. Falling back to default: '{default}'")
            return default
            
        raise Exception(f"Printer '{target}' not found and no fallback available.")

    def print_raw(self, data: bytes, printer_name: Optional[str] = None) -> bool:
        """Send bytes directly to the printer spooler bypassing driver rendering."""
        target = self.get_target_printer(printer_name)
        
        hPrinter = None
        try:
            # Open printer
            hPrinter = win32print.OpenPrinter(target)
            
            # Start Doc
            job_info = ("Nuvia Butik Raw Print", None, "RAW")
            job_id = win32print.StartDocPrinter(hPrinter, 1, job_info)
            win32print.StartPagePrinter(hPrinter)
            
            # Write data
            win32print.WritePrinter(hPrinter, data)
            
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
            
            logger.info(f"Successfully printed raw job {job_id} to {target}")
            return True
            
        except Exception as e:
            logger.error(f"Raw print failed: {e}")
            raise e
        finally:
            if hPrinter:
                win32print.ClosePrinter(hPrinter)
