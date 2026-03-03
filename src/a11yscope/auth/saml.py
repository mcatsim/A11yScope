"""SAML 2.0 SP support using authlib."""
from __future__ import annotations

import base64
import logging
import zlib
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

from a11yscope.config import get_settings

logger = logging.getLogger(__name__)

_idp_metadata: dict | None = None

NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
}


async def load_idp_metadata() -> dict:
    """Fetch and parse IdP metadata XML."""
    global _idp_metadata
    if _idp_metadata:
        return _idp_metadata

    settings = get_settings()
    if not settings.sso_saml_metadata_url:
        raise RuntimeError("SAML metadata URL not configured")

    async with httpx.AsyncClient() as http:
        resp = await http.get(settings.sso_saml_metadata_url)
        resp.raise_for_status()
        xml = resp.text

    root = ElementTree.fromstring(xml)  # nosec B314 — IdP metadata from configured URL, defusedxml TODO
    sso_elem = root.find(".//md:IDPSSODescriptor/md:SingleSignOnService[@Binding='urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect']", NS)
    slo_elem = root.find(".//md:IDPSSODescriptor/md:SingleLogoutService[@Binding='urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect']", NS)

    _idp_metadata = {
        "entity_id": root.get("entityID", ""),
        "sso_url": sso_elem.get("Location", "") if sso_elem is not None else "",
        "slo_url": slo_elem.get("Location", "") if slo_elem is not None else "",
    }
    return _idp_metadata


def create_authn_request(acs_url: str, relay_state: str = "") -> str:
    """Build a SAML AuthnRequest redirect URL."""
    if not _idp_metadata:
        raise RuntimeError("IdP metadata not loaded — call load_idp_metadata() first")

    settings = get_settings()
    entity_id = settings.sso_saml_entity_id or "a11yscope"

    authn_request = f"""<samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        AssertionConsumerServiceURL="{acs_url}"
        Destination="{_idp_metadata['sso_url']}"
        Issuer="{entity_id}"
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Version="2.0">
        <saml:Issuer>{entity_id}</saml:Issuer>
    </samlp:AuthnRequest>"""

    deflated = zlib.compress(authn_request.encode())[2:-4]
    encoded = base64.b64encode(deflated).decode()

    params = {"SAMLRequest": encoded}
    if relay_state:
        params["RelayState"] = relay_state

    return f"{_idp_metadata['sso_url']}?{urlencode(params)}"


def parse_saml_response(saml_response_b64: str) -> dict:
    """Parse a base64-encoded SAML Response and extract user attributes.

    NOTE: In production, you MUST validate the XML signature. This
    implementation extracts attributes for development/integration testing.
    """
    xml_bytes = base64.b64decode(saml_response_b64)
    root = ElementTree.fromstring(xml_bytes)  # nosec B314 — signature validation TODO, defusedxml TODO

    # Extract NameID
    name_id_elem = root.find(".//saml:Subject/saml:NameID", NS)
    name_id = name_id_elem.text if name_id_elem is not None else ""

    # Extract attributes
    attrs: dict[str, str] = {}
    for attr_elem in root.findall(".//saml:AttributeStatement/saml:Attribute", NS):
        attr_name = attr_elem.get("Name", "")
        value_elem = attr_elem.find("saml:AttributeValue", NS)
        if value_elem is not None and value_elem.text:
            attrs[attr_name] = value_elem.text

    return {
        "subject": name_id,
        "email": attrs.get("email", attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", name_id)),
        "display_name": attrs.get("displayName", attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name", "")),
        "groups": attrs.get("groups", attrs.get("http://schemas.xmlsoap.org/claims/Group", "")),
    }
