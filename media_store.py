import xml.etree.ElementTree as ET
from ContentDirectory import StorageFolder, VideoItem, Photo, Resource, NAMESPACES
import json
import requests

api = "https://yewtu.be/api/v1/"


def apiget(apimethod):
    req = requests.get(f"{api}{apimethod}").json
    return req


class MediaStore:
    def __init__(self, host_url):
        self.host_url = host_url

    def browse(self, object_id, base_url):
        items = []

        # ROOT LEVEL
        if object_id == "0":
            # Create two virtual folders
            items.append(
                StorageFolder(
                    id="trending",
                    parent_id="0",
                    title="Trending",
                    restricted="1",
                    storage_used="-1",
                )
            )
            items.append(
                StorageFolder(
                    id="search",
                    parent_id="0",
                    title="Search YouTube",
                    restricted="1",
                    storage_used="-1",
                )
            )

        elif object_id == "trending":
            trending_obj = apiget("trending")
            for v in trending_obj:
                items.append(
                    StorageFolder(
                        id=v["videoId"],
                        parent_id=object_id,
                        title=v["title"],
                        restricted="1",
                        storage_used="-1",
                    )
                )

        """
        # INSIDE "My Movies"
        elif object_id == "0/My Movies":
            for i in [1, 2, 3]:
                # We provide a dummy resource so the TV/Player thinks it's a playable file
                res = Resource(f"{base_url}video/{i}", "http-get:*:video/mp4:*")
                items.append(
                    VideoItem(
                        id=f"movie_{i}",
                        parent_id=object_id,
                        title=f"Movie Entry {i}",
                        restricted="1",
                        res=[res],
                    )
                )
        

        # INSIDE "Photos"
        elif object_id == "0/Photos":
            for i in [4, 5, 6]:
                res = Resource(f"{base_url}image/{i}", "http-get:*:image/jpeg:*")
                items.append(
                    Photo(
                        id=f"photo_{i}",
                        parent_id=object_id,
                        title=f"Photo Entry {i}",
                        restricted="1",
                        res=[res],
                    )
                )
        """
        didl = self._build_didl_lite_xml(items)
        return didl, len(items), len(items)

    def _build_didl_lite_xml(self, items):
        """Helper to wrap ContentDirectory items into DIDL-Lite root."""
        root = ET.Element(
            "DIDL-Lite",
            {
                "xmlns": NAMESPACES["didl_lite"],
                "xmlns:dc": NAMESPACES["dc"],
                "xmlns:upnp": NAMESPACES["upnp"],
                "xmlns:sec": NAMESPACES["sec"],
            },
        )
        for item in items:
            root.append(item.to_xml())
        return ET.tostring(root, encoding="unicode")
