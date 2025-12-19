import time
import uuid
import threading
from ssdp import SSDPServer
from dlna import DLNAServer

# Configuration
HOST = "0.0.0.0"
PORT = 8000

if __name__ == "__main__":
    # Generate a unique ID for this session (shared between HTTP and SSDP)
    server_uuid = uuid.uuid4()

    # Initialize the separated services
    http_service = DLNAServer(HOST, PORT)
    ssdp_service = SSDPServer(PORT, http_service.server_uuid)

    print("Starting DLNA services...")

    try:
        http_service.start()
        ssdp_service.start()

        print(f"DLNA Server running (UUID: {server_uuid})")
        print("Press Ctrl+C to stop.")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping services...")
        ssdp_service.stop()
        http_service.stop()
        print("Services stopped.")
