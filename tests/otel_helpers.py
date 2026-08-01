"""OpenTelemetry global-state helpers for tests.

The OTel Python API stores its tracer and meter providers in module globals
guarded by a ``Once``, so any test that installs its own provider has to reach
past the public API both to make the install take effect and to undo it. Doing
that by hand is subtly wrong in a way that poisons every later test in the same
xdist worker — see :func:`isolated_tracer_provider` for the mechanism.

Use these context managers instead of touching the globals directly.
"""

from contextlib import contextmanager

from opentelemetry import metrics as otel_metrics
from opentelemetry import trace

# The metrics globals live on the private submodule; `opentelemetry.metrics`
# only re-exports the public functions, so mutating them requires the real
# module object. `opentelemetry.trace` holds its own globals directly.
from opentelemetry.metrics import _internal as otel_metrics_internal


@contextmanager
def cleared_tracer_provider():
    """Clear the global tracer provider for the block, then fully restore.

    For code under test that installs its own provider (e.g. ``init_tracing``).
    See :func:`isolated_tracer_provider` for why restoration must go through
    ``trace._TRACER_PROVIDER`` and not ``trace.get_tracer_provider()``.
    """
    original = trace._TRACER_PROVIDER
    original_set_once_done = trace._TRACER_PROVIDER_SET_ONCE._done

    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False

    try:
        yield
    finally:
        trace._TRACER_PROVIDER = original
        trace._TRACER_PROVIDER_SET_ONCE._done = original_set_once_done


@contextmanager
def isolated_tracer_provider(provider: trace.TracerProvider):
    """Install ``provider`` as the global tracer provider, then fully restore.

    Save and restore ``trace._TRACER_PROVIDER`` directly rather than going
    through ``trace.get_tracer_provider()``. When nothing is set,
    ``get_tracer_provider()`` returns the module-level ``_PROXY_TRACER_PROVIDER``
    singleton, and ``ProxyTracerProvider.get_tracer`` delegates to whatever
    ``_TRACER_PROVIDER`` currently is. So "restoring" that return value installs
    the proxy as the global provider, and every subsequent ``get_tracer()`` call
    recurses into itself until it raises ``RecursionError``. That fails the rest
    of the worker's observability tests, and it only shows up when another
    module runs first, which is why it presented as a flake.

    Args:
        provider: Provider to install for the duration of the block.

    Yields:
        The provider that was installed.
    """
    original = trace._TRACER_PROVIDER
    original_set_once_done = trace._TRACER_PROVIDER_SET_ONCE._done

    # Clear the Once so set_tracer_provider actually takes effect; without this
    # it logs "Overriding of current TracerProvider is not allowed" and no-ops.
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace.set_tracer_provider(provider)

    try:
        yield provider
    finally:
        trace._TRACER_PROVIDER = original
        trace._TRACER_PROVIDER_SET_ONCE._done = original_set_once_done


@contextmanager
def isolated_meter_provider(provider: otel_metrics.MeterProvider):
    """Install ``provider`` as the global meter provider, then fully restore.

    The metrics API has the same first-writer-wins ``Once`` as the trace API, so
    a plain ``set_meter_provider()`` in a fixture silently no-ops once any other
    module has set one — the reader then collects nothing and
    ``get_metrics_data()`` returns ``None``. Clearing the ``Once`` first makes
    the install take effect; restoring it afterwards keeps the next module's
    fixture working too.

    ``_PROXY_METER_PROVIDER`` also caches the real provider (to back-fill
    instruments handed out before one was set), so that reference is saved and
    restored as well.

    Args:
        provider: Provider to install for the duration of the block.

    Yields:
        The provider that was installed.
    """
    mod = otel_metrics_internal
    original = mod._METER_PROVIDER
    original_set_once_done = mod._METER_PROVIDER_SET_ONCE._done
    original_proxy_target = mod._PROXY_METER_PROVIDER._real_meter_provider

    mod._METER_PROVIDER = None
    mod._METER_PROVIDER_SET_ONCE._done = False
    otel_metrics.set_meter_provider(provider)

    try:
        yield provider
    finally:
        mod._METER_PROVIDER = original
        mod._METER_PROVIDER_SET_ONCE._done = original_set_once_done
        mod._PROXY_METER_PROVIDER._real_meter_provider = original_proxy_target
