# niimblue

Python client library for **NiimBot** label printers, communicating with a
locally running [`niimblue-cli`](https://github.com/MultiMote/niimblue) REST
server over HTTP.

## Features

- Connect via **Bluetooth** or **USB**
- Print from a **file path** (str or `pathlib.Path`), **URL**, **raw bytes**, or a **Pillow image**
- Fetch structured **printer info** and **RFID consumable data**
- Scan for nearby devices
- Launch the `niimblue-cli` server subprocess from Python
- Optional Pillow dependency — core library works without it

## Requirements

- Python 3.10+
- [`niimblue-cli`](https://github.com/MultiMote/niimblue) on your `PATH`

## Installation

```bash
pip install niimblue              # core only
pip install "niimblue[pillow]"    # with Pillow support
```

## Quick start

```python
from niimblue import Printer, PrintJob, Transport, start_server

proc = start_server(port=5000)
try:
    with Printer("http://localhost:5000") as p:
        p.connect(Transport.SERIAL, "COM8")
        p.print(PrintJob(image_source="label.png"))   # str path or URL
finally:
    proc.terminate()
    proc.wait()
```

## Documentation

```bash
pip install "niimblue[docs]"
cd docs && make html
```

## License

MIT
