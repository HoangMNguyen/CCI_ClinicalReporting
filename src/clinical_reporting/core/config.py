"""Declarative report configuration.

:class:`ReportConfig` is a thin, typed wrapper around the settings dictionary
that :meth:`CLReport.save_setting_to_json` already produces. Reusing that exact
schema means every settings file saved from the UI is a valid configuration for
headless / programmatic runs -- no conversion required.

Typical tool-chaining usage::

    from clinical_reporting.core.config import ReportConfig
    from clinical_reporting.core.report import CLReport
    from clinical_reporting.services.loaders import read_data_dict_zip_corelisting
    from clinical_reporting.services.exporter import write_xlsx

    report = CLReport()
    report.set_data(read_data_dict_zip_corelisting("study_export.zip"))
    missing = report.apply_config(ReportConfig.from_settings_json("setting.json"))
    df = report.create_report()
    write_xlsx(df, "report.xlsx")
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

PathLike = Union[str, Path]


@dataclass
class ReportConfig:
    """A report configuration backed by the persisted settings schema.

    The configuration is stored verbatim in :attr:`raw` as the same dictionary
    structure used by the on-disk settings JSON, so it stays forward/backward
    compatible with files saved by the UI.
    """

    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportConfig":
        """Build a config from an in-memory settings dictionary."""
        return cls(deepcopy(dict(data)))

    @classmethod
    def from_settings_json(cls, file_path: PathLike) -> "ReportConfig":
        """Load a config from a settings JSON file written by the UI/engine."""
        with open(file_path, "r", encoding="utf-8") as handle:
            return cls(json.load(handle))

    def to_settings_json(self, file_path: PathLike) -> None:
        """Persist the configuration to a settings JSON file."""
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(self.raw, handle, indent=4)

    def to_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the underlying settings dictionary."""
        return deepcopy(self.raw)

    @property
    def study_name(self) -> Optional[str]:
        """Study name recorded in the configuration, if any."""
        return self.raw.get("study_name")

    @property
    def setting_name(self) -> Optional[str]:
        """Human-readable setting name recorded in the configuration, if any."""
        return self.raw.get("setting_name")
