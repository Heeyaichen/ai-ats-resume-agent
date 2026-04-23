"""Azure service adapters.

Each adapter wraps a single Azure SDK client and exposes exactly one
method that maps to one agent tool (design spec Section 4.3).
Adapters receive all config from Settings and all I/O is validated
against the Pydantic tool models in backend.app.models.tools.
"""
