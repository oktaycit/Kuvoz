#!/usr/bin/env python3
"""
DHT Native Test Script
Tests DHT11 sensor using DHT_Native library
"""

import sys
import time
sys.path.append('lib/')

try:
    from DHT_Native import read_retry
    print('Testing DHT11 with DHT_Native...')
    
    for i in range(3):
        hum, temp = read_retry(11, 15)
        if hum is not None and temp is not None:
            print(f'Attempt {i+1}: {temp:.1f}°C, {hum:.1f}%rH')
            break
        else:
            print(f'Attempt {i+1}: Failed')
            time.sleep(2)
    else:
        print('❌ All attempts failed!')
        sys.exit(1)
    
    print('✅ DHT11 native test completed successfully!')

except ImportError as e:
    print(f'❌ Import error: {e}')
    print('Make sure DHT_Native.py is in lib/ directory')
    sys.exit(1)
    
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)