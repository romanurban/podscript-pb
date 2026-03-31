#!/usr/bin/env python3

import psutil
import sys
import time

def check_system_resources():
    """Quick system resource check"""
    
    # Memory
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Disk space for output directory
    try:
        disk = psutil.disk_usage('.')
        disk_free_gb = disk.free / 1024 / 1024 / 1024
    except:
        disk_free_gb = 0
    
    print("🖥️  System Resource Check")
    print("=" * 30)
    print(f"Memory: {memory.percent:.1f}% used ({memory.available/1024/1024/1024:.1f}GB available)")
    print(f"Swap: {swap.percent:.1f}% used")
    print(f"CPU: {cpu_percent:.1f}% used")
    print(f"Disk space: {disk_free_gb:.1f}GB free")
    print()
    
    # Check if system is ready for transcription
    ready = True
    warnings = []
    
    if memory.percent > 80:
        warnings.append(f"⚠️  High memory usage: {memory.percent:.1f}%")
        if memory.percent > 90:
            ready = False
    
    if memory.available < 2 * 1024 * 1024 * 1024:  # Less than 2GB available
        warnings.append(f"⚠️  Low available memory: {memory.available/1024/1024/1024:.1f}GB")
        ready = False
    
    if swap.percent > 50:
        warnings.append(f"⚠️  High swap usage: {swap.percent:.1f}%")
    
    if disk_free_gb < 5:
        warnings.append(f"⚠️  Low disk space: {disk_free_gb:.1f}GB")
        if disk_free_gb < 1:
            ready = False
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if ready:
        print("✅ System ready for transcription")
        return True
    else:
        print("❌ System not recommended for long transcription")
        return False

if __name__ == "__main__":
    ready = check_system_resources()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force-check":
        sys.exit(0 if ready else 1)
    
    if not ready:
        print("\nRecommendations:")
        print("- Close other applications to free memory")
        print("- Restart system if swap usage is high")
        print("- Free up disk space if needed")
        print("- Consider using smaller chunk sizes")