import os
import time
import socket
import uuid
import threading
import platform
import mimetypes
import xml.etree.ElementTree as ET
import didl
from http.server import BaseHTTPRequestHandler, HTTPServer


class DLNAHTTPServer(HTTPServer):
    """Custom HTTPServer class that can store DLNAServer instance"""

    dlna_server: "DLNAServer" = None  # type: ignore


class ContentDirectory:
    def __init__(self, server):
        self.server = server
        self.system_update_id = 1
        self._create_example_content()

    def _create_example_content(self):
        self.content = {
            "0": {
                "id": "0",
                "title": "Root",
                "type": "container",
                "child_count": 3,
                "children": ["1", "2", "3"],
            },
            "1": {
                "id": "1",
                "title": "Videos",
                "type": "container",
                "child_count": 2,
                "children": ["11", "12"],
                "parent": "0",
            },
            "2": {
                "id": "2",
                "title": "Music",
                "type": "container",
                "child_count": 2,
                "children": ["21", "22"],
                "parent": "0",
            },
            "3": {
                "id": "3",
                "title": "Pictures",
                "type": "container",
                "child_count": 2,
                "children": ["31", "32"],
                "parent": "0",
            },
            "11": {
                "id": "11",
                "title": "Action Movies",
                "type": "container",
                "child_count": 2,
                "children": ["111", "112"],
                "parent": "1",
            },
            "12": {
                "id": "12",
                "title": "Comedy Movies",
                "type": "container",
                "child_count": 1,
                "children": ["121"],
                "parent": "1",
            },
            "111": {
                "id": "111",
                "title": "Action Movie 1",
                "type": "item",
                "class": "object.item.videoItem",
                "mime_type": "video/mp4",
                "size": "1073741824",
                "duration": "2:30:00",
                "parent": "11",
            },
            "112": {
                "id": "112",
                "title": "Action Movie 2",
                "type": "item",
                "class": "object.item.videoItem",
                "mime_type": "video/mp4",
                "size": "2147483648",
                "duration": "2:45:00",
                "parent": "11",
            },
            "121": {
                "id": "121",
                "title": "Comedy Movie 1",
                "type": "item",
                "class": "object.item.videoItem",
                "mime_type": "video/mp4",
                "size": "1073741824",
                "duration": "1:45:00",
                "parent": "12",
            },
            "21": {
                "id": "21",
                "title": "Rock",
                "type": "container",
                "child_count": 2,
                "children": ["211", "212"],
                "parent": "2",
            },
            "22": {
                "id": "22",
                "title": "Pop",
                "type": "container",
                "child_count": 1,
                "children": ["221"],
                "parent": "2",
            },
            "211": {
                "id": "211",
                "title": "Rock Song 1",
                "type": "item",
                "class": "object.item.audioItem",
                "mime_type": "audio/mpeg",
                "size": "5242880",
                "duration": "3:30",
                "parent": "21",
            },
            "212": {
                "id": "212",
                "title": "Rock Song 2",
                "type": "item",
                "class": "object.item.audioItem",
                "mime_type": "audio/mpeg",
                "size": "4194304",
                "duration": "3:15",
                "parent": "21",
            },
            "221": {
                "id": "221",
                "title": "Pop Song 1",
                "type": "item",
                "class": "object.item.audioItem",
                "mime_type": "audio/mpeg",
                "size": "6291456",
                "duration": "4:00",
                "parent": "22",
            },
            "31": {
                "id": "31",
                "title": "Nature",
                "type": "container",
                "child_count": 2,
                "children": ["311", "312"],
                "parent": "3",
            },
            "32": {
                "id": "32",
                "title": "City",
                "type": "container",
                "child_count": 1,
                "children": ["321"],
                "parent": "3",
            },
            "311": {
                "id": "311",
                "title": "Mountain Landscape",
                "type": "item",
                "class": "object.item.imageItem",
                "mime_type": "image/jpeg",
                "size": "2097152",
                "parent": "31",
            },
            "312": {
                "id": "312",
                "title": "Ocean Sunset",
                "type": "item",
                "class": "object.item.imageItem",
                "mime_type": "image/jpeg",
                "size": "3145728",
                "parent": "31",
            },
            "321": {
                "id": "321",
                "title": "City Skyline",
                "type": "item",
                "class": "object.item.imageItem",
                "mime_type": "image/jpeg",
                "size": "4194304",
                "parent": "32",
            },
        }

    def _data_to_didl_object(self, data):
        """Convert a dictionary from self.content to a DIDL object."""
        obj_type = data.get("type")
        if obj_type == "container":
            cls = (
                didl.type_by_upnp_class(data.get("class", "object.container"))
                or didl.Container
            )
            return cls(
                id=data["id"],
                parent_id=data.get("parent", "-1"),
                title=data["title"],
                restricted="1",
                child_count=str(data.get("child_count", 0)),
                never_playable="1",
            )

        if obj_type == "item":
            cls = didl.type_by_upnp_class(data["class"]) or didl.Item

            res = didl.Resource(
                uri=f"http://{self.server.host_ip}:{self.server.port}/media/{data['id']}",
                protocol_info=f"http-get:*:{data['mime_type']}:*",
                size=data.get("size"),
                duration=data.get("duration"),
            )

            return cls(
                id=data["id"],
                parent_id=data.get("parent", "-1"),
                title=data["title"],
                restricted="1",
                resources=[res],
            )

        return None

    def _generate_didl_objects(
        self,
        object_id,
        browse_flag="BrowseDirectChildren",
        starting_index=0,
        requested_count=0,
    ):
        didl_objects = []
        total_matches = 0

        if browse_flag == "BrowseMetadata":
            item_data = self.content.get(object_id)
            if item_data:
                didl_obj = self._data_to_didl_object(item_data)
                if didl_obj:
                    didl_objects.append(didl_obj)
                total_matches = 1 if didl_obj else 0

        elif browse_flag == "BrowseDirectChildren":
            parent_container_data = self.content.get(object_id)
            if parent_container_data and "children" in parent_container_data:
                children_ids = parent_container_data["children"]
                total_matches = len(children_ids)

                start = int(starting_index)
                req_count = int(requested_count)
                count = req_count if req_count > 0 else total_matches
                end = min(start + count, total_matches)

                for child_id in children_ids[start:end]:
                    child_data = self.content.get(child_id)
                    if child_data:
                        didl_obj = self._data_to_didl_object(child_data)
                        if didl_obj:
                            didl_objects.append(didl_obj)

        return didl_objects, total_matches

    def browse(
        self,
        object_id,
        browse_flag,
        filter,
        starting_index,
        requested_count,
        sort_criteria,
    ):
        didl_objects, total_matches = self._generate_didl_objects(
            object_id, browse_flag, starting_index, requested_count
        )

        didl_xml = didl.to_xml_string(*didl_objects).decode("utf-8")
        number_returned = len(didl_objects)

        return didl_xml, number_returned, total_matches, self.system_update_id

    def get_system_update_id(self):
        return str(self.system_update_id)

    def get_search_capabilities(self):
        return ""

    def get_sort_capabilities(self):
        return ""


class DLNAHttpRequestHandler(BaseHTTPRequestHandler):
    @property
    def dlna_server(self) -> "DLNAServer":
        """Get the DLNAServer instance from the HTTP server"""
        return getattr(self.server, "dlna_server", None)  # type: ignore

    def do_GET(self):
        req_path = self.path.lstrip("/")

        if ".." in req_path:
            self.send_error(403, "Forbidden")
            return

        if req_path == "description.xml":
            xml_content = self.dlna_server._generate_description_xml()
            if xml_content:
                self.send_response(200)
                self.send_header("Content-type", "application/xml; charset=utf-8")
                self.end_headers()
                self.wfile.write(xml_content.encode("utf-8"))
            else:
                self.send_error(404, "File Not Found")
            return

        if req_path == "icon.png":
            try:
                with open("web/icon.png", "rb") as f:
                    icon_data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(icon_data)
            except FileNotFoundError:
                self.send_error(404, "Icon not found")
            except IOError:
                self.send_error(500, "Error reading icon")
            return

        if req_path == "contentDirectory.xml":
            try:
                with open("web/contentdirectory.xml", "r") as f:
                    xml_content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/xml; charset=utf-8")
                self.end_headers()
                self.wfile.write(xml_content.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(404, "ContentDirectory service description not found")
            return

        if req_path == "connectionManager.xml":
            try:
                with open("web/connectionmanager.xml", "r") as f:
                    xml_content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/xml; charset=utf-8")
                self.end_headers()
                self.wfile.write(xml_content.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(404, "ConnectionManager service description not found")
            return

        if req_path == "MSMediaReceiverRegistrar.xml":
            try:
                with open("web/MSMediaReceiverRegistrar.xml", "r") as f:
                    xml_content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/xml; charset=utf-8")
                self.end_headers()
                self.wfile.write(xml_content.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(
                    404, "MSMediaReceiverRegistrar service description not found"
                )
            return

        if req_path.startswith("contentdirectory/"):
            self.send_error(404, "Resource not found")
            return

        if os.path.exists(req_path):
            mime_type, _ = mimetypes.guess_type(req_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            try:
                with open(req_path, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", mime_type)
                    self.end_headers()
                    self.wfile.write(f.read())
            except IOError:
                self.send_error(500, "Error reading file")
        else:
            self.send_error(404, "File Not Found")

    def _handle_soap_request(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Empty SOAP request")
            return

        soap_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")

        try:
            root = ET.fromstring(soap_body)
            action = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body/*")

            if action is None:
                self.send_error(400, "Invalid SOAP request")
                return

            action_name = action.tag.split("}")[-1] if "}" in action.tag else action.tag

            if action_name == "Browse":
                object_id = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}ObjectID", "0"
                )
                browse_flag = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}BrowseFlag",
                    "BrowseDirectChildren",
                )
                filter = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}Filter", "*"
                )
                starting_index = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}StartingIndex",
                    "0",
                )
                requested_count = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}RequestedCount",
                    "0",
                )
                sort_criteria = action.findtext(
                    "{urn:schemas-upnp-org:service-ContentDirectory:1}SortCriteria", ""
                )

                result, number_returned, total_matches, update_id = (
                    self.dlna_server.content_directory.browse(
                        object_id,
                        browse_flag,
                        filter,
                        starting_index,
                        requested_count,
                        sort_criteria,
                    )
                )

                response = self._generate_soap_response(
                    "Browse",
                    {
                        "Result": result,
                        "NumberReturned": str(number_returned),
                        "TotalMatches": str(total_matches),
                        "UpdateID": str(update_id),
                    },
                    "urn:schemas-upnp-org:service-ContentDirectory:1",
                )

            elif action_name == "GetSystemUpdateID":
                update_id = self.dlna_server.content_directory.get_system_update_id()
                response = self._generate_soap_response(
                    "GetSystemUpdateID",
                    {"Id": update_id},
                    "urn:schemas-upnp-org:service-ContentDirectory:1",
                )

            elif action_name == "GetSearchCapabilities":
                search_caps = (
                    self.dlna_server.content_directory.get_search_capabilities()
                )
                response = self._generate_soap_response(
                    "GetSearchCapabilities",
                    {"SearchCaps": search_caps},
                    "urn:schemas-upnp-org:service-ContentDirectory:1",
                )

            elif action_name == "GetSortCapabilities":
                sort_caps = self.dlna_server.content_directory.get_sort_capabilities()
                response = self._generate_soap_response(
                    "GetSortCapabilities",
                    {"SortCaps": sort_caps},
                    "urn:schemas-upnp-org:service-ContentDirectory:1",
                )

            else:
                self.send_error(401, f"Action {action_name} not implemented")
                return

            self.send_response(200)
            self.send_header("Content-type", "text/xml; charset=utf-8")
            self.send_header("EXT", "")
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))

        except ET.ParseError as e:
            self.send_error(400, f"Invalid XML: {e}")
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")

    def _generate_soap_response(self, action_name, arguments, service_ns):
        response = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:{action_name}Response xmlns:u="{service_ns}">"""

        for arg_name, arg_value in arguments.items():
            response += (
                f"\n      <{arg_name}>{self._escape_xml(str(arg_value))}</{arg_name}>"
            )

        response += f"""
    </u:{action_name}Response>
  </s:Body>
</s:Envelope>"""

        return response

    def _escape_xml(self, text):
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _handle_cm_soap_request(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Empty SOAP request")
            return

        soap_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")

        try:
            root = ET.fromstring(soap_body)
            action_node = root.find(
                ".//{http://schemas.xmlsoap.org/soap/envelope/}Body/*"
            )

            if action_node is None:
                self.send_error(400, "Invalid SOAP request")
                return

            action_name = (
                action_node.tag.split("}")[-1]
                if "}" in action_node.tag
                else action_node.tag
            )

            if action_name == "GetProtocolInfo":
                source_protocols = "http-get:*:video/mp4:*,http-get:*:audio/mpeg:*,http-get:*:image/jpeg:*"
                response = self._generate_soap_response(
                    "GetProtocolInfo",
                    {"Source": source_protocols, "Sink": ""},
                    "urn:schemas-upnp-org:service:ConnectionManager:1",
                )
            elif action_name == "GetCurrentConnectionIDs":
                response = self._generate_soap_response(
                    "GetCurrentConnectionIDs",
                    {"ConnectionIDs": "0"},
                    "urn:schemas-upnp-org:service:ConnectionManager:1",
                )
            elif action_name == "PrepareForConnection":
                response = self._generate_soap_response(
                    "PrepareForConnection",
                    {"ConnectionID": -1, "AVTransportID": -1, "RcsID": -1},
                    "urn:schemas-upnp-org:service:ConnectionManager:1",
                )
            else:
                self.send_error(501, f"Action {action_name} not implemented")
                return

            self.send_response(200)
            self.send_header("Content-type", "text/xml; charset=utf-8")
            self.send_header("EXT", "")
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))

        except ET.ParseError as e:
            self.send_error(400, f"Invalid XML: {e}")
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")

    def do_POST(self):
        if self.path == "/ContentDirectory/control":
            self._handle_soap_request()
            return
        elif self.path == "/ConnectionManager/control":
            self._handle_cm_soap_request()
            return
        elif self.path == "/MediaReceiverRegistrar/control":
            self.send_error(501, "Not Implemented")
            return

        print(f"Received unhandled POST request for URL: {self.path}")
        print("Headers:")
        for header, value in self.headers.items():
            print(f"  {header}: {value}")

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            post_content = self.rfile.read(content_length)
            print(f"Content:\n{post_content.decode('utf-8', errors='ignore')}")
        else:
            print("No content in POST request.")

        self.send_error(404, "Not Found")


class DLNAServer:
    def __init__(
        self,
        host_ip=None,
        port=8200,
    ):
        self.port = port
        self.host_ip = host_ip if host_ip else self._get_local_ip()
        self.uuid = uuid.uuid4()
        self.content_directory = ContentDirectory(self)

        self.httpd = None
        self.http_thread = None
        self.broadcast_thread = None
        self._stop_event = threading.Event()

    def _generate_description_xml(self):
        try:
            with open("web/description.xml", "r") as f:
                xml_template = f.read()
        except FileNotFoundError:
            print("Error: description.xml not found. Please ensure the file exists.")
            return ""

        xml = xml_template.replace("{{UUID}}", str(self.uuid)).replace(
            "{{NODE_NAME}}", platform.node()
        )
        return xml

    def _get_local_ip(self):
        try:
            hostname = socket.gethostname()
            _, _, ip_addresses = socket.gethostbyname_ex(hostname)

            non_loopback_ips = [
                ip
                for ip in ip_addresses
                if not ip.startswith("127.") and not ip.startswith("169.254.")
            ]

            if non_loopback_ips:
                return non_loopback_ips[0]

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("127.0.0.1", 80))
                IP = s.getsockname()[0]
                return IP
            except Exception as e:
                print(f"Error getting local IP: {e}")
                return "127.0.0.1"
            finally:
                s.close()
        except Exception as e:
            print(f"Error getting local IP: {e}")
            # General fallback if any of the above fails
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                IP = s.getsockname()[0]
                return IP
            except Exception as e:
                print(f"Error getting local IP: {e}")
                return "127.0.0.1"
            finally:
                s.close()

    def _run_http_server(self):
        server_address = (self.host_ip, self.port)
        self.httpd = DLNAHTTPServer(server_address, DLNAHttpRequestHandler)
        self.httpd.dlna_server = self  # Pass DLNAServer instance to the httpd

        print(f"Starting httpd on {self.host_ip}:{self.port}...")
        self.httpd.serve_forever()

    def _broadcast_presence(self):
        MCAST_GRP = "239.255.255.250"
        MCAST_PORT = 1900
        desc_path = "/description.xml"
        location = f"http://{self.host_ip}:{self.port}{desc_path}"
        server_sig = "DLNATube/1.0"

        targets = [
            "upnp:rootdevice",
            f"uuid:{self.uuid}",
            "urn:schemas-upnp-org:device:MediaServer:1",
        ]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        for target in targets:
            if target == f"uuid:{self.uuid}":
                usn = target
            else:
                usn = f"uuid:{self.uuid}::{target}"

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
