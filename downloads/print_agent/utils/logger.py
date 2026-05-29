import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import json

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config():
    config_path = os.path.join(get_base_path(), 'config.json')
    
    default_config = {
        "server": {"host": "0.0.0.0", "port": 3210},
        "security": {
            "auth_token": "NuviaSecretPrintToken2026",
            "allowed_origins": [
                "http://localhost", "https://localhost", 
                "https://nuviabutik.com", "https://www.nuviabutik.com"
            ]
        },
        "printer": {"default_name": "Xprinter_XP-470B", "fallback_to_default": True},
        "logging": {"log_dir": "C:\\PrintAgent\\logs", "level": "INFO"}
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Deep update default_config with loaded values to avoid KeyError
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in default_config:
                        default_config[k].update(v)
                    else:
                        default_config[k] = v
                return default_config
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    except Exception as e:
        return default_config

config = get_config()
log_dir = config['logging']['log_dir']

if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("PrintAgent")
logger.setLevel(getattr(logging, config['logging']['level'].upper(), logging.INFO))

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'agent.log'), 
    maxBytes=5*1024*1024, 
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
