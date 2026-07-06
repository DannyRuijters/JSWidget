"""
JSWidget - A lightweight anywidget-based IPython widget that renders
arbitrary JavaScript inside Jupyter notebooks.

Usage:
    from jswidget import JSWidget

    w = JSWidget(width=800, height=600)
    w.js_code = '''
        const canvas = document.createElement("canvas");
        canvas.width = opts.width;
        canvas.height = opts.height;
        el.appendChild(canvas);
    '''
    w.show()
"""

from jswidget.jswidget import JSWidget

__all__ = ["JSWidget"]
__version__ = "0.1.0"
