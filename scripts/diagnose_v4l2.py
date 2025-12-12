#!/usr/bin/env python3
import subprocess
import os

def run_command(cmd):
    print(f"--- Running: {' '.join(cmd)} ---")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Command failed with code {result.returncode}")
            print(result.stderr)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

def main():
    print("Gathering detailed V4L2 information...")
    
    # Check for v4l2-ctl
    print("Checking for /dev/video0...")
    if not os.path.exists('/dev/video0'):
        print("/dev/video0 does not exist!")
        return

    # List overall device info
    run_command(['v4l2-ctl', '-d', '/dev/video0', '--info'])
    
    # List supported formats
    run_command(['v4l2-ctl', '-d', '/dev/video0', '--list-formats-ext'])
    
    # List current parameters using v4l2-ctl
    run_command(['v4l2-ctl', '-d', '/dev/video0', '--get-parm'])

if __name__ == "__main__":
    main()
