from ssdp import DLNAServer
import time
import threading

if __name__ == "__main__":
    server = DLNAServer()
    server.start()
    print("DLNA server running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
