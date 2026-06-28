Quick start
===========

This page shows the minimal steps to get printing.
See :doc:`examples` for a full cookbook covering every feature.

Starting the server
-------------------

niimblue.py can launch the ``niimblue-cli server`` subprocess for you:

.. code-block:: python

   from niimblue import start_server

   proc = start_server(port=5000)   # blocks 1 s while the server warms up
   # ... do work ...
   proc.terminate()
   proc.wait()

Or manage it manually in a terminal:

.. code-block:: bash

   niimblue-cli server --port 5000

Connecting and printing
-----------------------

:class:`~niimblue.Printer` works as a context manager — it disconnects
automatically when the ``with`` block exits.

.. code-block:: python

   from pathlib import Path
   from niimblue import Printer, PrintJob, Transport, PrintDirection

   with Printer("http://localhost:5000") as p:

       # USB serial
       p.connect(Transport.SERIAL, "COM8")           # Windows
       # p.connect(Transport.SERIAL, "/dev/ttyUSB0") # Linux / macOS
       # p.connect(Transport.BLE, "AA:BB:CC:DD:EE:FF")

       assert p.is_connected()

       # str path, pathlib.Path, URL, or raw bytes — all accepted
       p.print(PrintJob(image_source="label.png"))
       p.print(PrintJob(image_source=Path("label.png")))
       p.print(PrintJob(
           image_source="https://example.com/label.png",
           label_width=344,
           label_height=200,
           print_direction=PrintDirection.TOP,
           quantity=2,
           density=4,
       ))

Using Pillow (optional)
-----------------------

Install the extra first::

   pip install "niimblue[pillow]"

Then pass a ``PIL.Image.Image`` directly to :class:`~niimblue.PrintJob`:

.. code-block:: python

   from PIL import Image, ImageDraw
   from niimblue import Printer, PrintJob, Transport

   img = Image.new("RGB", (344, 96), "white")
   ImageDraw.Draw(img).text((10, 30), "Hello, NiimBot!", fill="black")

   with Printer() as p:
       p.connect(Transport.SERIAL, "COM8")
       p.print(PrintJob(image_source=img))

Next steps
----------

* :doc:`examples` — full cookbook (batch printing, error handling, RFID, …)
* :doc:`api` — complete API reference
