"""Quick Kafka connection test"""
import socket
import sys

def test_port(host, port):
    """Test if port is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"[+] Port {port} is OPEN on {host}")
            return True
        else:
            print(f"[-] Port {port} is CLOSED on {host}")
            return False
    except Exception as e:
        print(f"[-] Error testing port: {e}")
        return False

def test_kafka_python():
    """Test Kafka Python client connection"""
    try:
        from kafka import KafkaConsumer
        from kafka.errors import NoBrokersAvailable
        
        print("\n[INFO] Testing Kafka Python client...")
        print("[INFO] Creating consumer with localhost:9092...")
        
        consumer = KafkaConsumer(
            bootstrap_servers=['localhost:9092'],
            consumer_timeout_ms=5000,
            api_version_auto_timeout_ms=5000,
            request_timeout_ms=10000,
            metadata_max_age_ms=5000
        )
        
        print("[+] Kafka connection SUCCESSFUL!")
        print(f"[+] Available topics: {consumer.topics()}")
        consumer.close()
        return True
        
    except NoBrokersAvailable as e:
        print(f"[-] NoBrokersAvailable: {e}")
        print("[INFO] Broker might be using KRaft mode or different listener configuration")
        return False
    except Exception as e:
        print(f"[-] Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("=== Kafka Connection Diagnostic ===\n")
    
    # Test 1: Port connectivity
    print("[1/2] Testing port connectivity...")
    port_open = test_port("localhost", 9092)
    
    # Test 2: Kafka Python client
    print("[2/2] Testing Kafka Python client...")
    kafka_works = test_kafka_python()
    
    print("\n=== Summary ===")
    print(f"Port 9092 reachable: {'YES' if port_open else 'NO'}")
    print(f"Kafka client works: {'YES' if kafka_works else 'NO'}")
    
    if port_open and not kafka_works:
        print("\n[!] Port is open but Kafka client cannot connect.")
        print("[!] This might be a KRaft configuration issue.")
        print("[!] Try checking KAFKA_HOME\\config\\kraft\\syniq-server.properties")
        print("[!] Look for 'listeners' and 'advertised.listeners' settings")
