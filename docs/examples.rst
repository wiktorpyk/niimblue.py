Examples
========

All examples assume the niimblue-cli server is already running.
Use :func:`~niimblue.start_server` to launch it from Python, or start it
manually with ``niimblue-cli server --port 5000``.

.. contents:: On this page
   :local:
   :depth: 1

----

Starting and stopping the server
---------------------------------

.. code-block:: python

    from niimblue import start_server

    # Launch niimblue-cli server in the background.
    # wait=1.5 sleeps 1.5 s to let the server bind before you connect.
    proc = start_server(port=5000, wait=1.5)

    # ... do your work ...

    proc.terminate()
    proc.wait()

Use it as a context manager with ``contextlib.closing`` for automatic cleanup:

.. code-block:: python

    import contextlib
    from niimblue import start_server, Printer, Transport

    proc = start_server(port=5000)
    with contextlib.closing(proc):
        with Printer() as p:
            p.connect(Transport.SERIAL, "COM8")
            # ...
        proc.terminate()   # closing() calls proc.close(), not terminate()

Or wrap everything in a helper:

.. code-block:: python

    import subprocess
    import contextlib
    from niimblue import start_server, Printer, Transport

    @contextlib.contextmanager
    def managed_printer(port=5000, **connect_kwargs):
        proc = start_server(port=port)
        try:
            with Printer(f"http://localhost:{port}") as p:
                p.connect(**connect_kwargs)
                yield p
        finally:
            proc.terminate()
            proc.wait()

    with managed_printer(transport=Transport.SERIAL, address="COM8") as p:
        print(p.info())

----

Connecting to a printer
------------------------

Serial (USB)
^^^^^^^^^^^^

.. code-block:: python

    from niimblue import Printer, Transport

    with Printer() as p:
        # Windows
        p.connect(Transport.SERIAL, "COM8")

        # Linux / macOS
        p.connect(Transport.SERIAL, "/dev/ttyUSB0")

        print("Battery:", p.info().charge, "%")

Bluetooth LE
^^^^^^^^^^^^

.. code-block:: python

    from niimblue import Printer, Transport

    with Printer() as p:
        # Scan first to find the address
        devices = p.scan(Transport.BLE)
        for d in devices:
            print(d.name, d.address)

        # Then connect by MAC
        p.connect(Transport.BLE, "AA:BB:CC:DD:EE:FF")

----

Printing images
---------------

From a file path (string or Path)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pathlib import Path
    from niimblue import Printer, PrintJob, Transport

    with Printer() as p:
        p.connect(Transport.SERIAL, "COM8")

        # str path
        p.print(PrintJob(image_source="label.png"))

        # pathlib.Path
        p.print(PrintJob(image_source=Path("assets/label.png")))

From a remote URL
^^^^^^^^^^^^^^^^^

.. code-block:: python

    from niimblue import Printer, PrintJob, Transport, PrintDirection

    with Printer() as p:
        p.connect(Transport.SERIAL, "COM8")
        p.print(PrintJob(
            image_source="https://example.com/barcode.png",
            label_width=344,
            label_height=96,
            print_direction=PrintDirection.TOP,
            quantity=1,
            density=4,
        ))

From raw bytes
^^^^^^^^^^^^^^

Useful when the image comes from a network response or an in-memory buffer:

.. code-block:: python

    import requests as req
    from niimblue import Printer, PrintJob, Transport

    image_bytes = req.get("https://example.com/label.png").content

    with Printer() as p:
        p.connect(Transport.SERIAL, "COM8")
        p.print(PrintJob(image_source=image_bytes))

From a Pillow image (optional dependency)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requires ``pip install "niimblue[pillow]"``.

.. code-block:: python

    from PIL import Image, ImageDraw, ImageFont
    from niimblue import Printer, PrintJob, Transport

    # Build the label in memory
    img = Image.new("RGB", (344, 96), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((8, 8),  "Product Name",  fill="black")
    draw.text((8, 40), "SKU: 00123456", fill="black")
    draw.rectangle([(0, 0), (343, 95)], outline="black", width=2)

    with Printer() as p:
        p.connect(Transport.SERIAL, "COM8")
        p.print(PrintJob(image_source=img, quantity=3))

----

Layout and quality options
---------------------------

.. code-block:: python

    from niimblue import PrintJob, PrintDirection, ImagePosition, ImageFit

    job = PrintJob(
        image_source="label.png",

        # Orientation
        print_direction=PrintDirection.TOP,   # portrait feed

        # Canvas size in pixels (auto-detected when omitted)
        label_width=344,
        label_height=200,

        # How to place the image inside the canvas
        image_position=ImagePosition.CENTRE,
        image_fit=ImageFit.CONTAIN,           # letterbox, preserve aspect ratio

        # Quality
        quantity=2,       # print 2 copies
        density=4,        # darker (range 1–5, default 3)
        threshold=140,    # binarisation threshold (0–255, default 128)

        # Hardware hint — auto-detected by the server when omitted
        print_task="B1",
        label_type=1,
    )

----

Checking printer status
------------------------

.. code-block:: python

    from niimblue import Printer, Transport

    with Printer() as p:
        p.connect(Transport.BLE, "AA:BB:CC:DD:EE:FF")

        info = p.info()
        print(f"Model:    {info.model}")
        print(f"Firmware: {info.software_version}")
        print(f"Battery:  {info.charge}%")
        print(f"DPI:      {info.dpi}")
        print(f"Density range: {info.density_min}–{info.density_max} "
              f"(default {info.density_default})")
        print(f"Detected task: {info.detected_print_task}")

----

Checking consumables via RFID
-------------------------------

.. code-block:: python

    from niimblue import Printer, Transport

    with Printer() as p:
        p.connect(Transport.SERIAL, "/dev/ttyUSB0")

        rfid = p.rfid()

        paper = rfid.paper
        print(f"Paper tag present: {paper.tag_present}")
        print(f"Labels remaining:  {paper.remaining_paper} / {paper.all_paper}")
        print(f"Barcode: {paper.bar_code}")

        if rfid.ribbon:
            ribbon = rfid.ribbon
            print(f"Ribbon remaining: {ribbon.remaining_paper} / {ribbon.all_paper}")

        # Warn when running low
        if paper.remaining_paper < 20:
            print("⚠ Paper roll almost empty — please replace soon.")

----

Batch printing
--------------

Print a list of labels generated on the fly, reusing one connection:

.. code-block:: python

    from PIL import Image, ImageDraw
    from niimblue import Printer, PrintJob, Transport

    ITEMS = [
        ("Apple",  "SKU-001"),
        ("Banana", "SKU-002"),
        ("Cherry", "SKU-003"),
    ]

    def make_label(name: str, sku: str) -> Image.Image:
        img = Image.new("RGB", (344, 96), "white")
        draw = ImageDraw.Draw(img)
        draw.text((8, 10), name, fill="black")
        draw.text((8, 50), sku,  fill="black")
        return img

    with Printer() as p:
        p.connect(Transport.SERIAL, "COM8")
        for name, sku in ITEMS:
            label = make_label(name, sku)
            msg = p.print(PrintJob(image_source=label))
            print(f"Printed {name}: {msg}")

----

Error handling
--------------

.. code-block:: python

    from niimblue import (
        Printer, PrintJob, Transport,
        PrinterConnectionError, PrinterPrintError,
    )

    with Printer("http://localhost:5000") as p:
        try:
            p.connect(Transport.SERIAL, "COM8")
        except PrinterConnectionError as e:
            print(f"Could not connect: {e}")
            raise SystemExit(1)

        try:
            p.print(PrintJob(image_source="label.png"))
        except PrinterPrintError as e:
            print(f"Print failed: {e}")
        except ValueError as e:
            # image_source was None or path didn't resolve
            print(f"Bad job configuration: {e}")
        except ImportError as e:
            # PIL.Image passed but Pillow not installed
            print(f"Missing dependency: {e}")

----

Custom server URL and timeout
------------------------------

Useful when the server runs on a remote machine or on a non-default port:

.. code-block:: python

    from niimblue import Printer, PrintJob, Transport

    # Remote server, longer timeout for slow networks
    with Printer(base_url="http://192.168.1.42:8080", timeout=30.0) as p:
        p.connect(Transport.BLE, "AA:BB:CC:DD:EE:FF")
        p.print(PrintJob(image_source="label.png"))
