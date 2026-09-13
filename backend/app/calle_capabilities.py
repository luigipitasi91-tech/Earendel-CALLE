import os
from dataclasses import asdict, dataclass

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException


@dataclass(frozen=True)
class ControlledRoute:
    region: str
    locale: str
    calling_code: str
    label: str
    evidence: str


# CALL-E's current SDK and API documentation use this exact route in their
# executable examples. The wider coverage table is not a runtime guarantee and
# explicitly warns that temporary restrictions can apply.
CONTROLLED_ROUTES = {
    ("US", "en-US"): ControlledRoute(
        region="US",
        locale="en-US",
        calling_code="+1",
        label="United States — English",
        evidence="CALL-E SDK 0.7.0 canonical create-call example",
    ),
}

# Observed against the live provider on 2026-09-13. Keep a known-rejected route
# closed even if it is accidentally added to CALLE_ENABLED_ROUTES.
KNOWN_RUNTIME_BLOCKS = {("GB", "en-GB")}


def _enabled_routes() -> set[tuple[str, str]]:
    configured = os.getenv("CALLE_ENABLED_ROUTES", "US:en-US")
    routes: set[tuple[str, str]] = set()
    for item in configured.split(","):
        region, separator, locale = item.strip().partition(":")
        if separator:
            routes.add((region.upper(), locale))
    return routes


def public_routes() -> list[dict]:
    enabled = _enabled_routes()
    return [
        asdict(route)
        for key, route in CONTROLLED_ROUTES.items()
        if key in enabled and key not in KNOWN_RUNTIME_BLOCKS
    ]


def check_route(*, phone: str, region: str, locale: str) -> tuple[bool, str]:
    region = (region or "").upper().strip()
    locale = (locale or "").strip()
    key = (region, locale)

    if key in KNOWN_RUNTIME_BLOCKS:
        return False, f"CALL-E currently rejects {region}/{locale}; no call was created."
    route = CONTROLLED_ROUTES.get(key)
    if route is None:
        return False, f"{region or 'UNKNOWN'}/{locale or 'UNKNOWN'} is not certified for this controlled live demo; no call was created."
    if key not in _enabled_routes():
        return False, f"{region}/{locale} is disabled by the server capability policy; no call was created."

    try:
        parsed = phonenumbers.parse(phone, None)
    except NumberParseException:
        return False, "Recipient phone is not valid E.164; no call was created."
    if not phonenumbers.is_valid_number(parsed):
        return False, "Recipient phone is not a valid callable number; no call was created."
    actual_region = phonenumbers.region_code_for_number(parsed)
    if actual_region != region:
        return False, f"Recipient number resolves to {actual_region or 'UNKNOWN'}, not {region}; no call was created."
    return True, "Route is certified and enabled for a controlled live trial. Runtime acceptance remains provider-controlled."
