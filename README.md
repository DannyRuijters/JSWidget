# JSWidget

A lightweight [anywidget](https://anywidget.dev/)-based IPython widget that renders arbitrary JavaScript (Canvas 2D, WebGL, etc.) inside Jupyter notebooks. It passes JSON data and binary buffers (mesh vertices, normals, indices) over the ipywidgets comm API, with live-update callbacks so Python can push new data without re-executing the cell.

Works in **VS Code**, **JupyterLab**, and **classic Jupyter notebooks** — no extra frontend build step required.

## Installation

```bash
pip install jswidget
```

Or install from source in development mode:

```bash
git clone https://github.com/DannyRuijters/JSWidget.git
cd JSWidget
pip install -e .
```

## Quick Start

```python
from jswidget import JSWidget

w = JSWidget(width=600, height=400)
w.js_code = '''
    const canvas = document.createElement("canvas");
    canvas.width = opts.width;
    canvas.height = opts.height;
    el.appendChild(canvas);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#e94560";
    ctx.font = "24px sans-serif";
    ctx.fillText("Hello from JSWidget!", 20, 50);
'''
w.show()
```

## JavaScript API

The JavaScript code passed to `js_code` receives the following variables:

| Variable | Description |
|---|---|
| `el` | Container DOM element to render into |
| `data` | JSON data dict set from Python via `w.data` |
| `getBuffer(name)` | Returns a named binary buffer as an `ArrayBuffer` |
| `opts` | `{width, height}` of the widget |
| `setState(obj)` | Save state that persists across re-renders |
| `getState()` | Retrieve previously saved state |
| `onData(fn)` | Register a callback for live `data` updates from Python |
| `onBuffers(fn)` | Register a callback for live buffer updates from Python |

## Passing Data

### JSON data

```python
w.data = {'values': [10, 40, 80], 'color': '#4ecdc4'}
# Update later (triggers onData callbacks in JS):
w.send_data({'values': [90, 20, 55], 'color': '#ff6b6b'})
```

### Binary buffers

```python
import numpy as np

vertices = np.array([[0,0,0],[1,0,0],[0,1,0]], dtype=np.float32)
normals  = np.array([[0,0,1],[0,0,1],[0,0,1]], dtype=np.float32)
indices  = np.array([0, 1, 2], dtype=np.uint32)

w.set_buffers(vertices=vertices, normals=normals, indices=indices)
```

Buffers are accessible in JavaScript via `getBuffer('vertices')`, etc., and return an `ArrayBuffer` that can be wrapped in a typed array (e.g. `new Float32Array(getBuffer('vertices'))`).

## Demo Notebook

See [JSWidget_demo.ipynb](JSWidget_demo.ipynb) for full examples including:

1. **Canvas 2D drawing** — gradient backgrounds and text rendering
2. **Bar chart with live updates** — pass data from Python via `send_data()` and re-draw with `onData()`
3. **Interactive WebGL mesh viewer** — sphere and torus rendering with mouse-drag rotation and scroll zoom, using binary buffers for mesh data

## Files

| File | Description |
|---|---|
| `jswidget.py` | The `JSWidget` class (anywidget-based DOMWidget with ESM frontend) |
| `JSWidget_demo.ipynb` | Demo notebook with Canvas 2D, bar chart, and WebGL examples |
| `LICENSE` | BSD 3-Clause License |

## License

BSD 3-Clause — see [LICENSE](LICENSE).
