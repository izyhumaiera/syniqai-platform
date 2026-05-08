"""Test socket connection to Kafka port"""
import socket

print("Testing Python socket connection to localhost:9092...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 9092))
    sock.close()
    
    print(f"Connection result code: {result}")
    
    if result == 0:
        print("✓ Port 9092 is OPEN - Kafka is reachable!")
    else:
        print(f"✗ Port 9092 is CLOSED (code: {result})")
        
except Exception as e:
    print(f"✗ Error: {e}")

# Also try with 127.0.0.1
print("\nTrying with 127.0.0.1...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', 9092))
    sock.close()
    
    print(f"Connection result code: {result}")
    
    if result == 0:
        print("✓ Port 9092 is OPEN via 127.0.0.1!")
    else:
        print(f"✗ Port 9092 is CLOSED via 127.0.0.1 (code: {result})")
        
except Exception as e:
    print(f"✗ Error: {e}")
