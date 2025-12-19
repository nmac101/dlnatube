import os
import platform
import uuid
import mimetypes
import threading
import socket
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

import ContentDirectory
from media_store import MediaStore

WEB_DIR = "web"


class DLNAHttpRequestHandler(BaseHTTPRequestHandler):
    """
    Handles SOAP control requests for ContentDirectory/ConnectionManager
    and GET requests for the device description.
    """

    def do_POST(self):
        # The paths here should match the <controlURL> defined in description.xml
        if self.path == "/ContentDirectory/control":
            self._handle_cd_soap_request()
        elif self.path == "/ConnectionManager/control":
            self._handle_cm_soap_request()
        else:
            self.send_error(404)

    def do_GET(self):
        req_path = self.path.lstrip("/")

        # 1. Device Description XML
        if req_path == "description.xml":
            self._serve_description()
            return

        # 2. Static Web Assets (Icons, etc.)
        web_file_path = os.path.join(WEB_DIR, req_path)
        if os.path.exists(web_file_path) and os.path.isfile(web_file_path):
            self._serve_file(web_file_path)
            return

        # 3. Media files / Resources
        if os.path.exists(req_path) and os.path.isfile(req_path):
            self._serve_file(req_path)
        else:
            self.send_error(404)

    def _handle_cd_soap_request(self):
        """Handle Content Directory 'Browse' requests using MediaStore."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        if "Browse" in body:
            try:
                # Extract the ObjectID (the folder the user is looking into)
                root = ET.fromstring(body)
                obj_id_node = root.find(".//ObjectID")
                object_id = obj_id_node.text if obj_id_node is not None else "0"

                # Get dynamic items from MediaStore
                base_url = f"http://{self.headers['Host']}/"
                (
                    didl_xml,
                    number_returned,
                    total_matches,
                ) = self.server.media_store.browse(object_id, base_url)

                # Build the SOAP response
                response = self._generate_soap_envelope(
                    "Browse",
                    {
                        "Result": didl_xml,
                        "NumberReturned": str(number_returned),
                        "TotalMatches": str(total_matches),
                        "UpdateID": "1",
                    },
                    "urn:schemas-upnp-org:service:ContentDirectory:1",
                )

                self._send_soap_response(response)
            except Exception as e:
                print(f"DLNA Browse Error: {e}")
                self.send_error(500)

    def _handle_cm_soap_request(self):
        """Basic Connection Manager response."""
        response = self._generate_soap_envelope(
            "GetProtocolInfo",
            {"Source": "http-get:*:*:*", "Sink": ""},
            "urn:schemas-upnp-org:service:ConnectionManager:1",
        )
        self._send_soap_response(response)

    def _build_didl_lite_xml(self, items):
        """Helper to wrap ContentDirectory items into DIDL-Lite root."""
        root = ET.Element(
            "DIDL-Lite",
            {
                "xmlns": ContentDirectory.NAMESPACES["didl_lite"],
                "xmlns:dc": ContentDirectory.NAMESPACES["dc"],
                "xmlns:upnp": ContentDirectory.NAMESPACES["upnp"],
                "xmlns:sec": ContentDirectory.NAMESPACES["sec"],
            },
        )
        for item in items:
            root.append(item.to_xml())
        return ET.tostring(root, encoding="unicode")

    def _generate_soap_envelope(self, action, args, ns):
        """Builds a standard SOAP envelope with XML-escaped arguments."""

        def escape_xml(v):
            return (
                str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )

        arg_xml = "".join([f"<{k}>{escape_xml(v)}</k>" for k, v in args.items()])
        return f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:{action}Response xmlns:u="{ns}">
      {arg_xml}
    </u:{action}Response>
  </s:Body>
</s:Envelope>"""

    def _serve_description(self):
        """Serves the description.xml with template replacements."""
        file_path = os.path.join(WEB_DIR, "description.xml")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace template tags
            content = content.replace("{{UUID}}", str(self.server.server_uuid))
            content = content.replace("{{NODE_NAME}}", platform.node())

            self.send_response(200)
            self.send_header("Content-type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(404)

    def _serve_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", mime_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500)

    def _send_soap_response(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


class DLNAServer:
    """
    The main DLNA HTTP Service.
    Manages the web server and the virtual MediaStore.
    """

    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.server_uuid = uuid.uuid4()
        host_url = f"http://{self._get_local_ip()}:{self.port}"
        self.media_store = MediaStore(host_url)
        self.httpd = None

    def start(self):
        self.httpd = HTTPServer((self.host, self.port), DLNAHttpRequestHandler)
        # Inject properties into the server instance so the Handler can access them
        self.httpd.server_uuid = self.server_uuid
        self.httpd.media_store = self.media_store

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"DLNA HTTP Service running at http://{self._get_local_ip()}:{self.port}")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            print("DLNA HTTP Service stopped.")

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
