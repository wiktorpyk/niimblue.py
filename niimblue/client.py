"""
niimblue.client
================

High-level Python client for NiimBot label printers via the
`niimblue-cli <https://github.com/MultiMote/niimblue>`_ REST server.

Typical usage::

    from niimblue import Printer, PrintJob, Transport, start_server

    proc = start_server(port=5000)          # launch niimblue-cli server
    with Printer("http://localhost:5000") as p:
        p.connect(Transport.SERIAL, "COM8")
        p.print(PrintJob(image_source="label.png"))
    proc.terminate()
"""

from __future__ import annotations

import base64
import io
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field

import requests

# ---------------------------------------------------------------------------
# Optional PIL dependency
# ---------------------------------------------------------------------------

try:
    from PIL import Image as _PILImage  # pip install pillow

    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PILImage = None  # type: ignore[assignment]
    _PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Transport(str, Enum):
    """Communication transport to use when connecting to the printer.

    Attributes:
        BLE: Bluetooth Low Energy.
        SERIAL: USB serial / UART.
    """

    BLE = "ble"
    SERIAL = "serial"


class PrintDirection(str, Enum):
    """Orientation of the printed image on the label.

    Attributes:
        LEFT: Feed direction is from the left (landscape).
        TOP: Feed direction is from the top (portrait).
    """

    LEFT = "left"
    TOP = "top"


class ImagePosition(str, Enum):
    """Anchor point for positioning the image within the label canvas.

    Attributes:
        CENTRE: Centered (default).
        TOP: Top-center.
        RIGHT_TOP: Top-right corner.
        RIGHT: Middle-right.
        RIGHT_BOTTOM: Bottom-right corner.
        BOTTOM: Bottom-center.
        LEFT_BOTTOM: Bottom-left corner.
        LEFT: Middle-left.
        LEFT_TOP: Top-left corner.
    """

    CENTRE = "centre"
    TOP = "top"
    RIGHT_TOP = "right top"
    RIGHT = "right"
    RIGHT_BOTTOM = "right bottom"
    BOTTOM = "bottom"
    LEFT_BOTTOM = "left bottom"
    LEFT = "left"
    LEFT_TOP = "left top"


class ImageFit(str, Enum):
    """Strategy used to fit the image into the label dimensions.

    Attributes:
        CONTAIN: Scale to fit, preserving aspect ratio (default).
        COVER: Scale to fill, cropping if necessary.
        FILL: Stretch to exactly fill (ignores aspect ratio).
        INSIDE: Like CONTAIN but never upscales.
        OUTSIDE: Like COVER but never downscales.
    """

    CONTAIN = "contain"
    COVER = "cover"
    FILL = "fill"
    INSIDE = "inside"
    OUTSIDE = "outside"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PrintJob:
    """Parameters for a single print job.

    The :attr:`image_source` field is flexible and accepts several types:

    * ``str`` — local file path *or* remote URL.
      If the path exists on disk it is read as a file; otherwise the string
      is sent to the server as a URL.
    * ``pathlib.Path`` — local image file (PNG, JPEG, BMP, …).
    * ``bytes`` — raw image bytes.
    * ``PIL.Image.Image`` — an already-opened Pillow image object
      (requires the ``pillow`` extra).

    Args:
        image_source: Image to print. See above for accepted types.
        print_direction: Feed direction / orientation of the label.
        label_width: Label width in pixels. Auto-detected when ``None``.
        label_height: Label height in pixels. Auto-detected when ``None``.
        image_position: Anchor point of the image within the label.
        image_fit: Resizing strategy.
        quantity: Number of copies to print.
        density: Print density (darkness). Typical range 1–5.
        threshold: Binarisation threshold for dithering (0–255, default 128).
        print_task: Hardware print-task code (e.g. ``"B1"``).
            Auto-detected by the server when ``None``.
        label_type: Label type identifier sent to the firmware.
    """

    image_source: Union[Path, str, bytes, Any, None] = None  # Any covers PIL.Image.Image

    # --- layout ---
    print_direction: PrintDirection = PrintDirection.LEFT
    label_width: Optional[int] = None
    label_height: Optional[int] = None
    image_position: ImagePosition = ImagePosition.CENTRE
    image_fit: ImageFit = ImageFit.CONTAIN

    # --- print quality ---
    quantity: int = 1
    density: int = 3
    threshold: int = 128

    # --- hardware hints ---
    print_task: Optional[str] = None
    label_type: int = 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_image(self) -> tuple[Optional[str], Optional[str]]:
        """Return ``(image_url, image_base64)``; exactly one value is non-None.

        A ``str`` source is first checked against the local filesystem.
        If the path exists the file is read; otherwise the string is
        forwarded to the server as a remote URL.

        Raises:
            ValueError: If :attr:`image_source` is ``None``.
            TypeError: If :attr:`image_source` is of an unsupported type.
            ImportError: If a ``PIL.Image.Image`` is supplied but Pillow is
                not installed.
        """
        src = self.image_source

        if src is None:
            raise ValueError("image_source must be set before printing.")

        raw: bytes

        if isinstance(src, str):
            p = Path(src)
            if p.exists():
                raw = p.read_bytes()
                return None, base64.b64encode(raw).decode()
            # Not a local file — treat as remote URL
            return src, None

        if isinstance(src, Path):
            raw = src.read_bytes()
            return None, base64.b64encode(raw).decode()

        if isinstance(src, bytes):
            return None, base64.b64encode(src).decode()

        if _PIL_AVAILABLE and isinstance(src, _PILImage.Image):  # type: ignore[union-attr]
            buf = io.BytesIO()
            src.save(buf, format="PNG")
            return None, base64.b64encode(buf.getvalue()).decode()

        if not _PIL_AVAILABLE and type(src).__name__ == "Image":
            raise ImportError(
                "Pillow is not installed. Install it with:  pip install pillow"
            )

        raise TypeError(
            f"Unsupported image_source type: {type(src).__name__}. "
            "Expected Path, str (file path or URL), bytes, or PIL.Image.Image."
        )

    def to_payload(self) -> dict[str, Any]:
        """Serialise the job to the JSON payload expected by the REST server.

        Returns:
            Dictionary ready to be JSON-encoded and POSTed to ``/print``.
        """
        image_url, image_b64 = self._resolve_image()

        payload: dict[str, Any] = {
            "printDirection": self.print_direction.value,
            "quantity": self.quantity,
            "density": self.density,
            "threshold": self.threshold,
            "labelType": self.label_type,
            "imagePosition": self.image_position.value,
            "imageFit": self.image_fit.value,
        }

        if image_url is not None:
            payload["imageUrl"] = image_url
        else:
            payload["imageBase64"] = image_b64

        if self.label_width is not None:
            payload["labelWidth"] = self.label_width
        if self.label_height is not None:
            payload["labelHeight"] = self.label_height
        if self.print_task is not None:
            payload["printTask"] = self.print_task

        return payload


@dataclass
class Device:
    """A printer device discovered during a scan.

    Attributes:
        name: Human-readable device name.
        address: BLE MAC address or serial port path.
    """

    name: str
    address: str


@dataclass
class PrinterInfo:
    """Structured printer information returned by :meth:`Printer.info`.

    Attributes:
        connect_result: Raw connection-result code from firmware.
        protocol_version: Firmware protocol version number.
        model_id: Numeric model identifier.
        serial: Device serial number string.
        mac: Bluetooth MAC address.
        charge: Battery charge percentage (0–100).
        auto_shutdown_time: Idle-shutdown timeout in seconds.
        label_type: Currently loaded label type code.
        hardware_version: Hardware revision string.
        software_version: Firmware version string.
        model: Human-readable model name (from server metadata).
        dpi: Print resolution in dots per inch.
        print_direction: Default print direction for this model.
        printhead_pixels: Number of pixels across the printhead.
        paper_types: List of supported paper/label type codes.
        density_min: Minimum valid density value.
        density_max: Maximum valid density value.
        density_default: Factory-default density value.
        detected_print_task: Print-task code auto-detected by the server.
    """

    connect_result: int
    protocol_version: int
    model_id: int
    serial: str
    mac: str
    charge: int
    auto_shutdown_time: int
    label_type: int
    hardware_version: str
    software_version: str
    model: str
    dpi: int
    print_direction: str
    printhead_pixels: int
    paper_types: list[int]
    density_min: int
    density_max: int
    density_default: int
    detected_print_task: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> PrinterInfo:
        """Construct a :class:`PrinterInfo` from the raw ``/info`` response dict."""
        pi = data["printerInfo"]
        mm = data["modelMetadata"]
        return cls(
            connect_result=pi["connectResult"],
            protocol_version=pi["protocolVersion"],
            model_id=pi["modelId"],
            serial=pi["serial"],
            mac=pi["mac"],
            charge=pi["charge"],
            auto_shutdown_time=pi["autoShutdownTime"],
            label_type=pi["labelType"],
            hardware_version=pi["hardwareVersion"],
            software_version=pi["softwareVersion"],
            model=mm["model"],
            dpi=mm["dpi"],
            print_direction=mm["printDirection"],
            printhead_pixels=mm["printheadPixels"],
            paper_types=mm["paperTypes"],
            density_min=mm["densityMin"],
            density_max=mm["densityMax"],
            density_default=mm["densityDefault"],
            detected_print_task=data["detectedPrintTask"],
        )


@dataclass
class RfidTagInfo:
    """RFID tag data for one consumable (paper roll or ribbon).

    Attributes:
        tag_present: ``True`` if a tag was detected.
        uuid: Tag UUID string.
        bar_code: Barcode value encoded in the tag.
        serial_number: Consumable serial number.
        all_paper: Total label capacity of the roll.
        used_paper: Number of labels already consumed.
        consumables_type: Numeric consumable-type identifier.
    """

    tag_present: bool
    uuid: str
    bar_code: str
    serial_number: str
    all_paper: int
    used_paper: int
    consumables_type: int

    @property
    def remaining_paper(self) -> int:
        """Remaining label count (``all_paper - used_paper``)."""
        return self.all_paper - self.used_paper

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RfidTagInfo:
        """Construct from the nested dict returned by ``/rfid``."""
        return cls(
            tag_present=d["tagPresent"],
            uuid=d["uuid"],
            bar_code=d["barCode"],
            serial_number=d["serialNumber"],
            all_paper=d["allPaper"],
            used_paper=d["usedPaper"],
            consumables_type=d["consumablesType"],
        )


@dataclass
class RfidInfo:
    """Combined RFID information for all loaded consumables.

    Attributes:
        paper: RFID data for the paper/label roll.
        ribbon: RFID data for the ink ribbon, or ``None`` for label-only
            printers.
    """

    paper: RfidTagInfo
    ribbon: Optional[RfidTagInfo] = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> RfidInfo:
        """Construct from the raw ``/rfid`` response dict."""
        ribbon_raw = data.get("ribbonRfidInfo")
        return cls(
            paper=RfidTagInfo.from_dict(data["paperRfidInfo"]),
            ribbon=RfidTagInfo.from_dict(ribbon_raw) if ribbon_raw else None,
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PrinterError(RuntimeError):
    """Base exception for all printer-client errors."""


class PrinterConnectionError(PrinterError):
    """Raised when the printer cannot be reached or a connection attempt fails."""


class PrinterPrintError(PrinterError):
    """Raised when a print job is rejected or fails mid-print."""


# ---------------------------------------------------------------------------
# Server launcher
# ---------------------------------------------------------------------------


def start_server(
    port: int = 5000,
    host: str = "127.0.0.1",
    extra_args: Optional[list[str]] = None,
    wait: float = 1.0,
    **popen_kwargs: Any,
) -> subprocess.Popen:  # type: ignore[type-arg]
    """Launch a ``niimblue-cli server`` subprocess.

    The function starts the server in the background and returns the
    :class:`subprocess.Popen` object so the caller can manage its lifetime.

    Args:
        port: TCP port for the REST server to listen on (default ``5000``).
        host: Host/interface to bind to (default ``"127.0.0.1"``).
        extra_args: Additional command-line arguments forwarded verbatim to
            ``niimblue-cli server``.
        wait: Seconds to sleep after spawning the process to give the server
            time to become ready (default ``1.0``). Pass ``0`` to skip.
        **popen_kwargs: Keyword arguments forwarded to :class:`subprocess.Popen`.

    Returns:
        The running server process.

    Raises:
        FileNotFoundError: If ``niimblue-cli`` is not found on ``PATH``.

    Example::

        proc = start_server(port=5000)
        try:
            with Printer("http://localhost:5000") as p:
                p.connect(Transport.SERIAL, "COM8")
                p.print(PrintJob(image_source="label.png"))
        finally:
            proc.terminate()
            proc.wait()
    """
    cmd = [
        "niimblue-cli",
        "server",
        "--port", str(port),
        "--host", host,
    ]
    if extra_args:
        cmd.extend(extra_args)

    proc = subprocess.Popen(cmd, **popen_kwargs)
    if wait > 0:
        time.sleep(wait)
    return proc


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Printer:
    """High-level client for the niimblue-cli REST server.

    Wraps every REST endpoint in a typed Python method.  Can be used as a
    context manager — :meth:`__exit__` disconnects automatically.

    Args:
        base_url: URL of the running niimblue-cli server
            (default: ``"http://localhost:5000"``).
        timeout: Seconds to wait for each HTTP response (default: ``10``).

    Example::

        with Printer("http://localhost:5000") as p:
            p.connect(Transport.BLE, "AA:BB:CC:DD:EE:FF")
            info = p.info()
            print(info.model, info.charge)
            p.print(PrintJob(image_source=Path("label.png")))
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> dict[str, Any]:
        response = self._session.get(f"{self.base_url}{path}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        response = self._session.post(
            f"{self.base_url}{path}",
            json=payload or {},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, transport: Union[Transport, str], address: str) -> str:
        """Connect to a printer.

        Args:
            transport: :class:`Transport` enum value, or the raw strings
                ``"ble"`` / ``"serial"``.
            address: BLE MAC address (e.g. ``"AA:BB:CC:DD:EE:FF"``) or serial
                port (e.g. ``"COM8"``, ``"/dev/ttyUSB0"``).

        Returns:
            Server confirmation message.

        Raises:
            PrinterConnectionError: If the server returns a non-2xx status.
        """
        if isinstance(transport, Transport):
            transport = transport.value
        try:
            result = self._post("/connect", {"transport": transport, "address": address})
            return result["message"]
        except requests.HTTPError as exc:
            raise PrinterConnectionError(
                f"Failed to connect to {address!r}: {exc}"
            ) from exc

    def disconnect(self) -> str:
        """Disconnect from the currently connected printer.

        Returns:
            Server confirmation message.
        """
        result = self._post("/disconnect")
        return result["message"]

    def is_connected(self) -> bool:
        """Return ``True`` if the server currently has an active printer connection."""
        return self._get("/connected")["connected"]

    # ------------------------------------------------------------------
    # Printer info
    # ------------------------------------------------------------------

    def info(self) -> PrinterInfo:
        """Fetch and return structured printer information.

        Returns:
            A populated :class:`PrinterInfo` instance.
        """
        return PrinterInfo.from_response(self._get("/info"))

    def rfid(self) -> RfidInfo:
        """Fetch and return RFID tag information for the loaded consumables.

        Returns:
            A populated :class:`RfidInfo` instance.
        """
        return RfidInfo.from_response(self._get("/rfid"))

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self, transport: Union[Transport, str]) -> list[Device]:
        """Scan for nearby devices over the given transport.

        Args:
            transport: :class:`Transport` enum value, or ``"ble"`` /
                ``"serial"``.

        Returns:
            List of discovered :class:`Device` objects (may be empty).
        """
        if isinstance(transport, Transport):
            transport = transport.value
        result = self._post("/scan", {"transport": transport})
        return [Device(name=d["name"], address=d["address"]) for d in result["devices"]]

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------

    def print(self, job: PrintJob) -> str:
        """Send a print job to the connected printer.

        Args:
            job: A fully configured :class:`PrintJob` instance.

        Returns:
            Server confirmation message.

        Raises:
            PrinterPrintError: If the server rejects the job.
            ValueError: If the job is missing an image source.
            TypeError: If ``image_source`` is of an unsupported type.
            ImportError: If a ``PIL.Image.Image`` is supplied but Pillow is
                not installed.
        """
        try:
            result = self._post("/print", job.to_payload())
            return result["message"]
        except requests.HTTPError as exc:
            raise PrinterPrintError(f"Print job failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> Printer:
        return self

    def __exit__(self, *_: Any) -> None:
        try:
            if self.is_connected():
                self.disconnect()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"Printer(base_url={self.base_url!r})"


# ---------------------------------------------------------------------------
# Example / smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    proc = start_server(port=5000, wait=1.5)
    try:
        with Printer("http://localhost:5000") as printer:
            printer.connect(Transport.SERIAL, "COM8")
            print("Connected:", printer.is_connected(), file=sys.stderr)
            print("Info:", printer.info(), file=sys.stderr)

            # From a local file path (str)
            printer.print(PrintJob(image_source="label.png"))

            # From a Path object
            printer.print(PrintJob(image_source=Path("label.png")))

            # From a URL
            printer.print(PrintJob(
                image_source="https://i.imgur.com/TzzVlc4.png",
                label_width=344,
                label_height=200,
                print_direction=PrintDirection.TOP,
                quantity=2,
            ))

            # From raw bytes
            printer.print(PrintJob(image_source=Path("label.png").read_bytes()))

            if _PIL_AVAILABLE:
                img = _PILImage.new("RGB", (200, 100), color="white")
                printer.print(PrintJob(image_source=img))
    finally:
        proc.terminate()
        proc.wait()
