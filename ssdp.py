import base64
import socket
import uuid
import time
import threading
import platform
from http.server import BaseHTTPRequestHandler, HTTPServer


DESCRIPTION_XML_TEMPLATE = f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dlna="urn:schemas-dlna-org:device-1-0" xmlns:sec="http://www.sec.co.kr/dlna">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <dlna:X_DLNACAP/>
    <dlna:X_DLNADOC>DMS-1.50</dlna:X_DLNADOC>
    <UDN>uuid:{uuid.uuid4()}</UDN>
    <dlna:X_DLNADOC>M-DMS-1.50</dlna:X_DLNADOC>
    <friendlyName>DLNATube</friendlyName>
    <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
    <manufacturer>nmac101</manufacturer>
    <manufacturerURL>https://github.com/nmac101/dlnatube</manufacturerURL>
    <modelName>DLNATube</modelName>
    <modelDescription></modelDescription>
    <modelNumber>Running on {platform.node()}</modelNumber>
    <modelURL></modelURL>
    <serialNumber></serialNumber>
    <sec:ProductCap>smi,DCM10,getMediaInfo.sec,getCaptionInfo.sec</sec:ProductCap>
    <sec:X_ProductCap>smi,DCM10,getMediaInfo.sec,getCaptionInfo.sec</sec:X_ProductCap>
    <iconList>
      <icon>
        <mimetype>image/png</mimetype>
        <width>128</width>
        <height>128</height>
        <depth>24</depth>
        <url>/icon.png</url>
      </icon>
    </iconList>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
        <SCPDURL>/contentDirectory.xml</SCPDURL>
        <controlURL>/serviceControl</controlURL>
        <eventSubURL></eventSubURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
        <SCPDURL>/connectionManager.xml</SCPDURL>
        <controlURL>/serviceControl</controlURL>
        <eventSubURL></eventSubURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:X_MS_MediaReceiverRegistrar:1</serviceType>
        <serviceId>urn:microsoft.com:serviceId:X_MS_MediaReceiverRegistrar</serviceId>
        <SCPDURL>/MSMediaReceiverRegistrar.xml</SCPDURL>
        <controlURL>/serviceControl</controlURL>
        <eventSubURL></eventSubURL>
      </service>
    </serviceList>
  </device>
</root>"""

server_icon = """
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
"""


class DLNAHttpRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/description.xml":
            self.send_response(200)
            self.send_header("Content-type", "application/xml")
            self.end_headers()
            xml = DESCRIPTION_XML_TEMPLATE
            self.wfile.write(xml.encode("utf-8"))
        elif self.path == "/icon.png":
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.end_headers()
            self.wfile.write(base64.b64decode(server_icon))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Quiet the HTTP server logging
        return


class DLNAServer:
    def __init__(
        self,
        host_ip=None,
        port=8200,
    ):
        self.port = port
        self.host_ip = host_ip if host_ip else self._get_local_ip()

        self.httpd = None
        self.http_thread = None
        self.broadcast_thread = None
        self._stop_event = threading.Event()

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable
            s.connect(("10.255.255.255", 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = "127.0.0.1"
        finally:
            s.close()
        return IP

    def _run_http_server(self):
        server_address = (self.host_ip, self.port)
        self.httpd = HTTPServer(server_address, DLNAHttpRequestHandler)

        print(f"Starting httpd on {self.host_ip}:{self.port}...")
        self.httpd.serve_forever()

    def _broadcast_presence(self):
        MCAST_GRP = "239.255.255.250"
        MCAST_PORT = 1900
        desc_path = "/description.xml"
        location = f"http://{self.host_ip}:{self.port}{desc_path}"
        server_sig = "Linux/3.14 UPnP/1.0 MyPythonDLNA/1.0"

        targets = [
            "upnp:rootdevice",
            "uuid:12345678-1234-1234-1234-123456789012",
            "urn:schemas-upnp-org:device:MediaServer:1",
        ]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        for target in targets:
            if target == "uuid:12345678-1234-1234-1234-123456789012":
                usn = target
            else:
                usn = f"uuid:12345678-1234-1234-1234-123456789012::{target}"

            packet = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {MCAST_GRP}:{MCAST_PORT}\r\n"
                "CACHE-CONTROL: max-age=1800\r\n"
                f"LOCATION: {location}\r\n"
                f"NT: {target}\r\n"
                "NTS: ssdp:alive\r\n"
                f"SERVER: {server_sig}\r\n"
                f"USN: {usn}\r\n"
                "\r\n"
            )

            try:
                sock.sendto(packet.encode("utf-8"), (MCAST_GRP, MCAST_PORT))
            except Exception as e:
                print(f"Failed to send for {target}: {e}")

        sock.close()

    def _run_broadcaster(self):
        while not self._stop_event.is_set():
            self._broadcast_presence()
            self._stop_event.wait(30)

    def start(self):
        self._stop_event.clear()

        self.http_thread = threading.Thread(target=self._run_http_server)
        self.http_thread.daemon = True
        self.http_thread.start()

        time.sleep(0.1)
        print(f"Broadcasting DLNA presence for {self.host_ip}...")
        self.broadcast_thread = threading.Thread(target=self._run_broadcaster)
        self.broadcast_thread.daemon = True

        self.broadcast_thread.start()

        print("DLNA server started.")

    def stop(self):
        print("Stopping DLNA server...")
        self._stop_event.set()

        if self.httpd:
            self.httpd.shutdown()

        if self.broadcast_thread:
            self.broadcast_thread.join()

        if self.http_thread:
            self.http_thread.join()

        print("DLNA server stopped.")


if __name__ == "__main__":
    server = DLNAServer()
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
