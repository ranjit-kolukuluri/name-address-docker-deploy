# utils/logger.py
"""
Simple logging utility
"""

from datetime import datetime
from typing import List, Dict


class SimpleLogger:
    """Simple logger for the application"""
    
    def __init__(self, max_logs: int = 500):
        self.logs: List[Dict] = []
        self.max_logs = max_logs
        self.enabled = True
    
    def log(self, message: str, category: str = "GENERAL", level: str = "INFO"):
        """Log a message"""
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now(),
            'level': level.upper(),
            'category': category.upper(),
            'message': message
        }
        
        self.logs.append(log_entry)
        
        # Maintain log size
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        # Console output
        timestamp_str = log_entry['timestamp'].strftime("%H:%M:%S")
        print(f"[{timestamp_str}] {level.upper()} {category}: {message}")
    
    def info(self, message: str, category: str = "GENERAL"):
        """Log info message"""
        self.log(message, category, "INFO")
    
    def warning(self, message: str, category: str = "GENERAL"):
        """Log warning message"""
        self.log(message, category, "WARNING")
    
    def error(self, message: str, category: str = "GENERAL"):
        """Log error message"""
        self.log(message, category, "ERROR")
    
    def get_recent_logs(self, count: int = 10) -> List[Dict]:
        """Get recent logs"""
        return self.logs[-count:] if self.logs else []
    
    def clear(self):
        """Clear all logs"""
        self.logs = []
        self.log("Logger cleared", "SYSTEM", "INFO")


# Global logger instance
logger = SimpleLogger()