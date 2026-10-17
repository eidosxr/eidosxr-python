import json
import re
import os
import sys
import time
import tempfile
import webbrowser
from typing import get_args
import jinja2
from jsonpatch import JsonPatch
from pydantic import ConfigDict, ValidationError, model_serializer, model_validator
from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ErrorType

from .root import EidosSpecification
from .data import EidosData
from .vegaspec import TopLevelSpec
from .exceptions import EidosError, EidosSpecError
from .. import version
from .._optional import import_optional

# The data helpers below (isotime, EidosDatasource, EidosChart) need pandas,
# geopandas, xarray, oceanum or altair — the optional data extra (pip install
# 'eidosxr[data]') — so they import them when called, not here.

__all__ = ["Eidos", "EidosDatasource", "EidosChart", "isotime"]

EIDOS_RENDERER = os.environ.get(
    "EIDOS_RENDERER",
    f"https://render.eidos.oceanum.io/v{version.__version__.split('.')[0]}.{version.__version__.split('.')[1]}",
)
TEMPLATES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "./_templates/"
)
j2_loader = jinja2.FileSystemLoader(TEMPLATES_PATH)
j2_env = jinja2.Environment(loader=j2_loader, trim_blocks=True)


_ERROR_TYPES = set(get_args(ErrorType))


def _line_error(err):
    """Turn a reported validation error back into one that can be raised."""
    if err["type"] in _ERROR_TYPES:
        return {k: err[k] for k in ("type", "loc", "input", "ctx") if k in err}
    # A custom error type (PydanticCustomError): keep its formatted message.
    return {
        "type": PydanticCustomError(err["type"], err["msg"]),
        "loc": err["loc"],
        "input": err["input"],
    }


class Eidos(EidosSpecification):
    """Eidos base class. This is the EIDOS base specification.

    Top-level keys starting with ``x-`` are extension metadata: they are kept as
    given (any JSON value) and written back out on dump. Any other unknown
    top-level key is rejected.
    """

    # The root schema allows ^x- keys alongside its properties (patternProperties
    # with additionalProperties false). datamodel-codegen cannot express that, so
    # the generated EidosSpecification forbids all extra keys; this hand-written
    # subclass allows extras and rejects the ones that are not x- keys.
    model_config = ConfigDict(extra="allow")

    _checkpoint = None

    @model_validator(mode="wrap")
    @classmethod
    def _only_extension_keys(cls, data, handler):
        # One extra_forbidden error per non-x- unknown key, located at the key,
        # reported together with any field errors, as extra="forbid" did.
        unknown = []
        if isinstance(data, dict):
            unknown = [
                {"type": "extra_forbidden", "loc": (k,), "input": v}
                for k, v in data.items()
                if k not in cls.model_fields and not k.startswith("x-")
            ]
        try:
            model = handler(data)
        except ValidationError as e:
            # model_validate runs Eidos.__init__ inside the handler, which
            # validates (and reports the unknown keys) again: don't repeat them.
            reported = {
                tuple(err["loc"])
                for err in e.errors()
                if err["type"] == "extra_forbidden"
            }
            unknown = [u for u in unknown if u["loc"] not in reported]
            if not unknown:
                raise
            errors = [_line_error(err) for err in e.errors()] + unknown
            raise ValidationError.from_exception_data(cls.__name__, errors) from None
        if unknown:
            raise ValidationError.from_exception_data(cls.__name__, unknown)
        return model

    @model_serializer(mode="wrap")
    def _keep_null_extension_keys(self, handler, info):
        # exclude_none (which model_dump always sets) would drop an x- key whose
        # value is null; it is extension data, not an unset field, so keep it.
        data = handler(self)
        if info.exclude_none:
            for key, value in (self.__pydantic_extra__ or {}).items():
                if (
                    value is None
                    and (info.include is None or key in info.include)
                    and not (info.exclude and key in info.exclude)
                ):
                    data[key] = None
        return data

    def __setattr__(self, name, value):
        # With extra="allow" pydantic stores an unknown attribute before the
        # validators run, so reject a non-x- name here, as extra="forbid" did.
        if not (name.startswith(("_", "x-")) or name in type(self).model_fields):
            raise EidosSpecError(
                ValidationError.from_exception_data(
                    type(self).__name__,
                    [
                        {
                            "type": "no_such_attribute",
                            "loc": (name,),
                            "input": value,
                            "ctx": {"attribute": name},
                        }
                    ],
                )
            )
        super().__setattr__(name, value)

    @classmethod
    def from_dict(cls, spec: dict):
        """Initialize Eidos class."""
        return cls(**spec)

    @classmethod
    def from_json(cls, spec: str):
        """Initialize Eidos class from json."""
        return cls.from_dict(json.loads(spec))

    def __init__(self, **spec):
        """Initialize Eidos class."""
        super().__init__(**spec)
        self._checkpoint = self.model_dump()

    def __str__(self):
        """Return string representation of Eidos class."""
        return self.model_dump_json(indent=2)

    def _change(self):
        """Change."""
        pass
        # print(f"EIDOS spec changed: {update}")

    def model_dump(self, **kwargs):
        """Dump model as dictionary."""
        return super().model_dump(**{**kwargs, "exclude_none": True})

    def model_dump_json(self, **kwargs):
        """Dump model as JSON, leaving out unset (None) fields as model_dump does."""
        return super().model_dump_json(**{**kwargs, "exclude_none": True})

    def diff(self):
        """Get diff since last checkpoint and reset checkpoint"""
        old = self._checkpoint
        self._checkpoint = self.model_dump()
        return (old, self._checkpoint)

    def patch(self):
        """Diff as JSON patch"""
        old, new = self.diff()
        return JsonPatch.from_diff(old, new).patch

    def spec(self):
        """Return the full EIDOS specification."""
        return self.model_dump()

    def html(self, title=None, renderer=EIDOS_RENDERER, height="99vh", width="99vw"):
        """Return the EIDOS specification as a displayable HTML page."""
        template = j2_env.get_template("index.j2")
        return template.render(
            spec=self.model_dump_json(exclude_none=True),
            title=title or self.name or "EIDOS",
            renderer=renderer,
            height=height,
            width=width,
        )

    def show(self, renderer=EIDOS_RENDERER):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(self.html(renderer).encode())
            f.close()
            url = "file://{}".format(f.name)
            time.sleep(1.0)
            return webbrowser.open_new_tab(url)


def _is_instance(data, module: str, cls: str) -> bool:
    """isinstance against a data-extra class without importing its library: an
    instance can only exist if the library is already loaded."""
    mod = sys.modules.get(module)
    return mod is not None and isinstance(data, getattr(mod, cls))


def isotime(x):
    t = import_optional("pandas").Timestamp(x)
    if not t.tz:
        t = t.tz_localize("UTC")
    return t.isoformat()


class EidosDatasource(EidosData):
    """Convenience class to create Eidos :class:`eidos.Datasource` from python data objects. Use these objects in the root level data field of the Eidos spec.

    Args:
        id (str): The ID of the datasource.
        data (DataFrame, GeoDataFrame, Dataset, OceanQL Query): The data to be used for the datasource.
        coordkeys (dict): The coordinate keys for the data. Default is empty dict.

    Raises:
        EidosError: If an invalid inline data type is provided.
        ImportError: If a library the data type needs is missing
            (pip install 'eidosxr[data]').

    """

    def __init__(self, id, data, coordkeys={}):
        if _is_instance(data, "geopandas", "GeoDataFrame"):
            data = data.__geo_interface__
            data["coordkeys"] = {**coordkeys, "g": "geometry"}
            dstype = "geojson"
        elif _is_instance(data, "pandas", "DataFrame"):
            import_optional("xarray")  # DataFrame.to_xarray needs it
            data = data.to_xarray()
            dstype = "dataset"
        elif _is_instance(data, "xarray", "Dataset"):
            dstype = "dataset"
        elif _is_instance(data, "oceanum.datamesh", "Query"):
            # Only explicitly-set fields: datamesh Query defaults (e.g.
            # resample='linear') are not valid in the EIDOS oceanql schema.
            data = json.loads(
                data.model_dump_json(exclude_none=True, exclude_defaults=True)
            )
            dstype = "oceanql"
        else:
            raise EidosError("Invalid inline data type")
        if dstype == "dataset":
            rename = {v: re.sub(r"[^a-zA-Z0-9_]", "_", v) for v in data.variables}
            _data = data.rename(rename)
            data = {
                "attributes": _data.attrs,
                "dimensions": dict(_data.sizes),
                "coordkeys": coordkeys,
            }
            data["variables"] = {}
            for v in _data.variables:
                dtype = str(_data.variables[v].dtype)
                values = _data.variables[v].to_dict()["data"]
                if dtype == "object":
                    if len(_data.variables[v].dims) > 1:
                        raise EidosError(
                            "Multi-dimensional object variables not supported"
                        )
                    values = [str(x) for x in values]
                    dtype = "string"
                elif dtype.startswith("datetime64"):
                    # The schema has no datetime dtype — times go over the wire
                    # as ISO 8601 strings, which the renderer normalises.
                    values = [isotime(x) for x in values]
                    dtype = "string"
                data["variables"][v] = {
                    "data": values,
                    "dimensions": _data.variables[v].dims,
                    "attributes": _data.variables[v].attrs,
                    "dtype": dtype,
                }
            if "t" in coordkeys:  # Sanitize time data to iso8601 strings
                if coordkeys["t"] in data["variables"]:
                    data["variables"][coordkeys["t"]]["data"] = [
                        isotime(x) for x in data["variables"][coordkeys["t"]]["data"]
                    ]
                    data["variables"][coordkeys["t"]]["dtype"] = "string"

        super().__init__(id=id, dataType=dstype, dataSpec=data)


class EidosChart(TopLevelSpec):
    """Convenience class to create :class:`eidos.TopLevelSpec` for a :class:`eidos.PlotView` node from Altair Chart. Use this object for the plotSpec field.
    To use one of the defined EIDOS datasources in the Altair Chart, use a :class:`altair.NamedData` object with the id of the :class:`eidos.Datasource` as the Altair.Chart constructor data arg.

    Args:
        chart (altair.Chart): The Altair Chart to be used for the plot.
    Raises:
        EidosError: If an invalid chart type is provided.
    """

    def __init__(self, chart):
        if not isinstance(chart, import_optional("altair").Chart):
            raise EidosError("Invalid chart type - must be an Altair Chart object")
        super().__init__(chart)
