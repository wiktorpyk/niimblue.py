Installation
============

Requirements
------------

* Python 3.10 or newer
* `niimblue-cli`_ installed and available on your ``PATH``

.. _niimblue-cli: https://github.com/MultiMote/niimblue

Core install
------------

.. code-block:: bash

   pip install git+https://github.com/wiktorpyk/niimblue.py.git

With Pillow support
-------------------

To enable printing from ``PIL.Image.Image`` objects, install the optional
``pillow`` extra:

.. code-block:: bash

   pip install "niimblue[pillow] @ git+https://github.com/wiktorpyk/niimblue.py.git"

Building the docs
-----------------

.. code-block:: bash

   pip install "niimblue[docs] @ git+https://github.com/wiktorpyk/niimblue.py.git"
   cd docs
   make html

The generated HTML will be in ``docs/_build/html/``.