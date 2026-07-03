"""
Custom DOMWidget that renders arbitrary JavaScript and passes data
(including binary buffers for mesh data) over the ipywidgets comm API.

Uses anywidget for reliable rendering in VS Code, JupyterLab, and classic notebooks.
No external dependencies beyond anywidget and numpy.

Usage:
    from jswidget_anywidget import JSWidget
    import numpy as np

    w = JSWidget(width=800, height=600)

    # Set binary buffers (mesh data)
    vertices = np.array([[0,0,0],[1,0,0],[0,1,0]], dtype=np.float32)
    indices = np.array([0,1,2], dtype=np.uint32)
    w.set_buffers(vertices=vertices, normals=normals, indices=indices)

    # Set JSON data
    w.data = {'opacity': 0.8, 'color': [1, 0, 0]}

    # Set JavaScript code and display
    w.js_code = '''
        const canvas = document.createElement('canvas');
        canvas.width = opts.width;
        canvas.height = opts.height;
        el.appendChild(canvas);
        const ctx = canvas.getContext('2d');

        // Access binary buffers
        const verts = new Float32Array(getBuffer('vertices'));

        // Access JSON data
        const opacity = data.opacity;

        // Register for live updates from Python
        onData((newData) => { ... });
        onBuffers((newMeta) => { ... });

        // Save state to survive re-renders
        setState({rotX: 0.3, rotY: 0.5});
    '''
    w.show()
"""

import numpy as np
import traitlets
import anywidget

# The ESM frontend module - provides the same JS API as jswidget.py
_ESM = """
function render({ model, el }) {
    // Create container
    const container = document.createElement('div');
    container.style.width = model.get('width') + 'px';
    container.style.height = model.get('height') + 'px';
    container.style.overflow = 'hidden';
    container.style.position = 'relative';
    el.appendChild(container);

    let cleanupFn = null;
    const _id = Math.random().toString(36).slice(2, 14);

    function executeCode() {
        const code = model.get('js_code');
        if (!code) return;

        // Cleanup previous execution
        if (cleanupFn) {
            try { cleanupFn(); } catch(e) {}
            cleanupFn = null;
        }
        container.innerHTML = '';

        // State management
        window.__jsw_state = window.__jsw_state || {};
        function setState(obj) { window.__jsw_state[_id] = Object.assign(window.__jsw_state[_id] || {}, obj); }
        function getState() { return window.__jsw_state[_id] || {}; }

        // opts
        const opts = { width: model.get('width'), height: model.get('height') };

        // data
        let currentData = model.get('data') || {};

        // getBuffer
        function getBuffer(name) {
            const raw = model.get('_buf_' + name);
            if (!raw) return null;
            if (raw instanceof DataView) {
                if (raw.byteLength === 0) return null;
                return raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength);
            }
            if (raw instanceof ArrayBuffer) {
                return raw.byteLength === 0 ? null : raw;
            }
            if (raw.buffer instanceof ArrayBuffer) {
                if (raw.byteLength === 0) return null;
                return raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength);
            }
            return null;
        }

        // Callback registries
        const _dataCallbacks = [];
        const _bufferCallbacks = [];
        function onData(fn) { _dataCallbacks.push(fn); }
        function onBuffers(fn) { _bufferCallbacks.push(fn); }

        // Wire up model change events to callbacks
        function _onDataChange() {
            currentData = model.get('data') || {};
            _dataCallbacks.forEach(fn => fn(currentData));
        }
        function _onBuffersChange() {
            const meta = model.get('_buffers_metadata') || [];
            _bufferCallbacks.forEach(fn => fn(meta));
        }
        model.on('change:data', _onDataChange);
        model.on('change:_buffers_metadata', _onBuffersChange);

        // Register cleanup to remove listeners
        cleanupFn = () => {
            model.off('change:data', _onDataChange);
            model.off('change:_buffers_metadata', _onBuffersChange);
        };

        try {
            const fn = new Function('el', 'data', 'getBuffer', 'opts', 'setState', 'getState', 'onData', 'onBuffers', code);
            fn(container, currentData, getBuffer, opts, setState, getState, onData, onBuffers);
        } catch(e) {
            const errDiv = document.createElement('pre');
            errDiv.style.color = 'red';
            errDiv.style.padding = '10px';
            errDiv.textContent = 'JS Error: ' + e.message + '\\n' + e.stack;
            container.appendChild(errDiv);
            console.error('JSWidget execution error:', e);
        }
    }

    // Execute initial code
    executeCode();

    // Re-execute when js_code changes
    model.on('change:js_code', executeCode);

    // Update container size
    model.on('change:width', () => {
        container.style.width = model.get('width') + 'px';
    });
    model.on('change:height', () => {
        container.style.height = model.get('height') + 'px';
    });

    return () => {
        if (cleanupFn) {
            try { cleanupFn(); } catch(e) {}
        }
    };
}
export default { render };
"""


class JSWidget(anywidget.AnyWidget):
    """A DOMWidget that renders arbitrary JavaScript with binary data.
    Uses anywidget for reliable comm-based rendering in all environments.

    The JavaScript code receives:
        el            - the container DOM element
        data          - the JSON data dict
        getBuffer(n)  - get named buffer as ArrayBuffer
        opts          - {width, height}
        setState(obj) - save state that persists across re-renders
        getState()    - retrieve previously saved state
        onData(fn)    - register callback for data updates
        onBuffers(fn) - register callback for buffer updates
    """

    _esm = _ESM

    # User-provided JavaScript code to execute in the widget
    js_code = traitlets.Unicode('').tag(sync=True)

    # JSON-serializable data dict passed to JavaScript
    data = traitlets.Dict({}).tag(sync=True)

    # Widget dimensions
    width = traitlets.Int(800).tag(sync=True)
    height = traitlets.Int(600).tag(sync=True)

    # Pre-defined binary buffer traitlets
    _buf_vertices = traitlets.Bytes(b'').tag(sync=True)
    _buf_normals = traitlets.Bytes(b'').tag(sync=True)
    _buf_indices = traitlets.Bytes(b'').tag(sync=True)
    _buf_data = traitlets.Bytes(b'').tag(sync=True)

    # Metadata about binary buffers (triggers onBuffers callback in JS)
    _buffers_metadata = traitlets.List([]).tag(sync=True)

    def set_buffers(self, **named_buffers):
        """Set binary data buffers for the JavaScript frontend.

        Each keyword argument should be a numpy array, bytes, or bytearray.

        Example:
            w.set_buffers(vertices=vertices, normals=normals, indices=indices)
        """
        metadata = []
        with self.hold_sync():
            for name, buf in named_buffers.items():
                trait_name = f'_buf_{name}'
                if not self.has_trait(trait_name):
                    self.add_traits(**{trait_name: traitlets.Bytes(b'').tag(sync=True)})

                if isinstance(buf, np.ndarray):
                    metadata.append({'name': name, 'dtype': str(buf.dtype), 'shape': list(buf.shape)})
                    setattr(self, trait_name, buf.tobytes())
                elif isinstance(buf, (bytes, bytearray, memoryview)):
                    metadata.append({'name': name, 'dtype': 'bytes', 'shape': [len(buf)]})
                    setattr(self, trait_name, bytes(buf))
                else:
                    raise TypeError(f"Buffer '{name}' must be numpy array, bytes, or bytearray")

            self._buffers_metadata = metadata

    def send_data(self, data_dict):
        """Update the data dict and push to JavaScript."""
        self.data = data_dict

    def execute(self, js_code):
        """Update the JavaScript code and re-render."""
        self.js_code = js_code

    def show(self):
        """Display the widget."""
        from IPython.display import display
        display(self)
