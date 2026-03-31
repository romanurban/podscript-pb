#!/usr/bin/env python3

import time
import psutil
import signal
import sys
import json
from datetime import datetime

class ProcessMonitor:
    def __init__(self, log_file="output/process_monitor.log"):
        self.log_file = log_file
        self.start_time = time.time()
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\n⚠️  Received signal {signum}, shutting down monitor...")
        self.running = False
    
    def log_system_stats(self):
        """Log current system stats to file"""
        timestamp = datetime.now().isoformat()
        uptime = time.time() - self.start_time
        
        # System memory and CPU
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Process info
        try:
            current_process = psutil.Process()
            process_memory = current_process.memory_info().rss / 1024 / 1024  # MB
            process_cpu = current_process.cpu_percent()
        except psutil.NoSuchProcess:
            process_memory = 0
            process_cpu = 0
        
        stats = {
            "timestamp": timestamp,
            "uptime_seconds": round(uptime, 1),
            "system": {
                "memory_percent": memory.percent,
                "memory_available_mb": round(memory.available / 1024 / 1024, 1),
                "cpu_percent": cpu_percent,
                "swap_percent": psutil.swap_memory().percent
            },
            "process": {
                "memory_mb": round(process_memory, 1),
                "cpu_percent": process_cpu
            }
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats) + "\n")
        
        return stats
    
    def monitor(self, interval=60):
        """Monitor system resources during transcription"""
        print(f"🔍 Starting process monitor (logging to {self.log_file})")
        print(f"📊 Check interval: {interval} seconds")
        
        # Ensure output directory exists
        import os
        os.makedirs("output", exist_ok=True)
        
        while self.running:
            try:
                stats = self.log_system_stats()
                
                # Print warning if resources are high
                if stats["system"]["memory_percent"] > 85:
                    print(f"⚠️  High memory usage: {stats['system']['memory_percent']:.1f}%")
                
                if stats["system"]["cpu_percent"] > 90:
                    print(f"⚠️  High CPU usage: {stats['system']['cpu_percent']:.1f}%")
                
                # Sleep with interrupt checking
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️  Monitor error: {e}")
                time.sleep(interval)
        
        print("✓ Process monitor stopped")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    monitor = ProcessMonitor()
    monitor.monitor(interval)