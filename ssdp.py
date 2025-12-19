import socket
import time
import threading

MCAST_GRP = "239.255.255.250"
MCAST_PORT = 1900

class SSDPServer:
    def __init__(self, port, server_uuid):
        self.port = port
        self.server_uuid = server_uuid
        self._stop_event = threading.Event()
        self.thread = None

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    def _broadcast_presence(self):
        ip = self._get_local_ip()
        location = f"http://{ip}:{self.port}/description.xml"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        targets = [
            "upnp:rootdevice",
            f"uuid:{self.server_uuid}",
            "urn:schemas-upnp-org:device:MediaServer:1",
        ]

        try:
            for target in targets:
                msg = (
                    f"NOTIFY * HTTP/1.1\r\n"
                    f"HOST: {MCAST_GRP}:{MCAST_PORT}\r\n"
                    f"CACHE-CONTROL: max-age=1800\r\n"
                    f"LOCATION: {location}\r\n"
                    f"NT: {target}\r\n"
                    f"NTS: ssdp:alive\r\n"
                    f"USN: uuid:{self.server_uuid}::{target}\r\n\r\n"
                )
                sock.sendto(msg.encode(), (MCAST_GRP, MCAST_PORT))
        except Exception as e:
            print(f"SSDP Broadcast error: {e}")
        finally:
            sock.close()

    def start(self):
        def broadcast_loop():
            # Initial burst
            self._broadcast_presence()
            while not self._stop_event.is_set():
                time.sleep(30)
                if not self._stop_event.is_set():
                    self._broadcast_presence()

        self.thread = threading.Thread(target=broadcast_loop, daemon=True)
        self.thread.start()
        print("SSDP Broadcaster started.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        print("SSDP Broadcaster stopped.")
