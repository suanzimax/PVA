"""Unified EPICS CA/PVA subscription helpers.

This module abstracts creating monitors for a list of PVs so that the
existing monitoring scripts can work with either Channel Access (CA)
via pyepics or PVAccess (PVA) via p4p.

Usage pattern (in scripts):

    from client_utils import create_monitors

    def on_update(pvname, value, timestamp):
        ...  # existing logic

    monitors, backend = create_monitors(CAMERA_PVS, protocol, on_update)

    # monitors: list of monitor handles (pyepics PV objects or p4p Monitor objects)
    # backend:  context object for PVA (p4p.client.thread.Context) or None for CA.

All scripts run until Ctrl+C. On KeyboardInterrupt you may optionally
call `cleanup_monitors(monitors, backend)` to close PVA context.
"""

from __future__ import annotations

from typing import Callable, List, Tuple, Optional, Any


def create_monitors(pv_names: List[str], protocol: str, user_callback: Callable[[str, Any, Optional[float]], None]) -> Tuple[List[Any], Optional[Any]]:
    """Create monitors for given PV names using selected protocol.

    Args:
        pv_names: list of PV names.
        protocol: 'ca' or 'pva'.
        user_callback: callable(pvname, value, timestamp_seconds|None)

    Returns:
        (monitors, backend_context)
    """
    protocol = protocol.lower()
    if protocol not in ("ca", "pva"):
        raise ValueError("protocol must be 'ca' or 'pva'")

    if protocol == "ca":
        try:
            from epics import PV  # type: ignore
        except ImportError as e:
            raise RuntimeError("pyepics not installed. Install with: pip install pyepics") from e

        monitors = []
        for pv in pv_names:
            # Wrap to normalize signature to user_callback(pvname, value, ts)
            def _cb(value=None, timestamp=None, pvname=pv, **k):  # pyepics passes pvname separately, but we bind here
                user_callback(pvname, value, timestamp)
            monitors.append(PV(pv, auto_monitor=True, callback=_cb))
        return monitors, None

    # PVA path
    try:
        from p4p.client.thread import Context  # type: ignore
    except ImportError as e:
        raise RuntimeError("p4p not installed. Install with: pip install p4p") from e

    ctxt = Context('pva')  # you could also allow configuration via env
    monitors = []

    def make_cb(pvname: str):
        def _cb(val):
            # Attempt to extract timestamp (normative type)
            ts = None
            try:
                # val.timeStamp has (secondsPastEpoch, nanoseconds)
                ts = val.timeStamp.secondsPastEpoch + val.timeStamp.nanoseconds * 1e-9  # type: ignore[attr-defined]
            except Exception:
                pass
            # Extract actual numeric/array payload if nested
            data = val
            for key in ("value", "data"):  # common normative field names
                if hasattr(data, key):
                    try:
                        data = getattr(data, key)
                    except Exception:
                        pass
            user_callback(pvname, data, ts)
        return _cb

    for pv in pv_names:
        monitors.append(ctxt.monitor(pv, make_cb(pv)))

    return monitors, ctxt


def cleanup_monitors(monitors: List[Any], backend: Optional[Any]) -> None:
    """Attempt to release resources (mainly for PVA context)."""
    try:
        if backend is not None:  # p4p Context
            backend.close()
    except Exception:
        pass
