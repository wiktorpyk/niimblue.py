"""
niimblue
=========

Python client library for NiimBot label printers via the
`niimblue-cli <https://github.com/MultiMote/niimblue>`_ REST server.

Quick start::

    from niimblue import Printer, PrintJob, Transport, PrintDirection, start_server
    from pathlib import Path

    proc = start_server(port=5000)
    try:
        with Printer("http://localhost:5000") as p:
            p.connect(Transport.SERIAL, "COM8")
            p.print(PrintJob(image_source=Path("label.png")))
    finally:
        proc.terminate()
        proc.wait()
"""

from niimblue.client import (
    # enums
    Transport,
    PrintDirection,
    ImagePosition,
    ImageFit,
    # data classes
    PrintJob,
    Device,
    PrinterInfo,
    RfidTagInfo,
    RfidInfo,
    # exceptions
    PrinterError,
    PrinterConnectionError,
    PrinterPrintError,
    # server launcher
    start_server,
    # main client
    Printer,
)

__all__ = [
    "Transport",
    "PrintDirection",
    "ImagePosition",
    "ImageFit",
    "PrintJob",
    "Device",
    "PrinterInfo",
    "RfidTagInfo",
    "RfidInfo",
    "PrinterError",
    "PrinterConnectionError",
    "PrinterPrintError",
    "start_server",
    "Printer",
]

__version__ = "0.1.0"
