import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import ctypes
import os

class PrintAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "NuviaPrintAgent"
    _svc_display_name_ = "Nuvia Local Print Agent"
    _svc_description_ = "Handles direct RAW/TSPL printing from remote Nuvia Butik server."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        
    def SvcDoRun(self):
        import uvicorn
        from main import app, config
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Run uvicorn without auto-reload in service
        uvicorn.run(
            app, 
            host=config['server']['host'], 
            port=config['server']['port'],
            log_level="info"
        )

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    if not is_admin():
        print("Please run this script as Administrator to install/start the service.")
        sys.exit(1)
        
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PrintAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PrintAgentService)
