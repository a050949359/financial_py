from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib


CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / CONFIG_FILE_NAME
DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[1] / "registry.d"


class ConfigValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SystemConfig:
    config_path: Path
    project_root: Path
    db_driver: str
    db_path: Path
    source_dir: Path
    log_path: Path
    log_retention_days: int
    debug: bool


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    config_path: Path
    project_root: Path
    api_endpoint: str
    api_url: str
    schema_path: Path
    table_name: str
    json_name: str
    json_path: Path


@dataclass(frozen=True)
class DatasetDefaults:
    api_endpoint: str
    schema_path: str
    table_name: str
    json_name: str


def _build_dataset_defaults(dataset_name: str, raw_config: dict) -> DatasetDefaults:
    return DatasetDefaults(
        api_endpoint=_require_non_empty_text(
            raw_config.get("api_endpoint"),
            f"registry.{dataset_name}.api_endpoint",
        ),
        schema_path=_require_non_empty_text(
            raw_config.get("schema_path"),
            f"registry.{dataset_name}.schema_path",
        ),
        table_name=_require_non_empty_text(
            raw_config.get("table_name"),
            f"registry.{dataset_name}.table_name",
        ),
        json_name=_require_non_empty_text(
            raw_config.get("json_name"),
            f"registry.{dataset_name}.json_name",
        ),
    )


@lru_cache(maxsize=1)
def _load_dataset_defaults_registry() -> dict[str, DatasetDefaults]:
    if not DEFAULT_REGISTRY_DIR.is_dir():
        raise ConfigValidationError(f"找不到 dataset registry 目錄: {DEFAULT_REGISTRY_DIR}")

    registry: dict[str, DatasetDefaults] = {}
    for registry_file in sorted(DEFAULT_REGISTRY_DIR.glob("*.toml")):
        dataset_name = registry_file.stem
        with registry_file.open("rb") as file_handle:
            raw_config = tomllib.load(file_handle)
        registry[dataset_name] = _build_dataset_defaults(dataset_name, raw_config)

    if not registry:
        raise ConfigValidationError(f"dataset registry 為空: {DEFAULT_REGISTRY_DIR}")

    return registry


def _resolve_dataset_defaults(dataset_name: str) -> DatasetDefaults:
    dataset_defaults = _load_dataset_defaults_registry().get(dataset_name)
    if dataset_defaults is not None:
        return dataset_defaults

    supported_datasets = ", ".join(sorted(_load_dataset_defaults_registry()))
    raise ConfigValidationError(
        f"未知的 dataset: {dataset_name}。支援項目: {supported_datasets}"
    )


def find_config_path(start_path: Path | None = None) -> Path:
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    start = (start_path or Path(__file__)).resolve()
    search_roots = [start.parent] if start.is_file() else [start]
    search_roots.append(Path.cwd().resolve())

    for root in search_roots:
        current = root
        while True:
            candidate = current / CONFIG_FILE_NAME
            if candidate.exists():
                return candidate
            if current.parent == current:
                break
            current = current.parent

    raise FileNotFoundError(f"找不到 {CONFIG_FILE_NAME}")


def _resolve_path(project_root: Path, value: str, fallback: str) -> Path:
    raw = Path(value or fallback)
    return raw if raw.is_absolute() else project_root / raw


def _load_system_config(config: dict) -> dict:
    return config.get("system", {})


def _parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _require_non_empty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{field_name} 不可為空")
    return value.strip()


@lru_cache(maxsize=16)
def _load_config_dict(resolved_config_path: Path) -> dict:
    with resolved_config_path.open("rb") as file_handle:
        return tomllib.load(file_handle)


@lru_cache(maxsize=16)
def _resolve_config_path(config_path: Path | None = None) -> Path:
    return (config_path or find_config_path()).resolve()


def get_raw_config(config_path: Path | None = None) -> dict:
    resolved_config_path = _resolve_config_path(config_path)
    return _load_config_dict(resolved_config_path)


def get_system_config(config_path: Path | None = None) -> SystemConfig:
    resolved_config_path = _resolve_config_path(config_path)
    project_root = resolved_config_path.parent
    config = get_raw_config(resolved_config_path)

    system_config = _load_system_config(config)
    db_driver = _require_non_empty_text(
        system_config.get("db_driver", "sqlite"),
        "system.db_driver",
    )

    return SystemConfig(
        config_path=resolved_config_path,
        project_root=project_root,
        db_driver=db_driver,
        db_path=_resolve_path(
            project_root,
            str(system_config.get("db_path", "")),
            "database/twse.db",
        ),
        source_dir=_resolve_path(
            project_root,
            str(system_config.get("source_dir", "")),
            "Source",
        ),
        log_path=_resolve_path(
            project_root,
            str(system_config.get("log_path", "")),
            "log",
        ),
        log_retention_days=int(system_config.get("log_retention_days", 30)),
        debug=_parse_bool(system_config.get("debug", False)),
    )


def get_dataset_config(
    dataset_name: str,
    config_path: Path | None = None,
) -> DatasetConfig:
    resolved_config_path = _resolve_config_path(config_path)
    project_root = resolved_config_path.parent
    config = get_raw_config(resolved_config_path)

    system_config = _load_system_config(config)
    dataset_config = config.get(dataset_name, {})
    dataset_defaults = _resolve_dataset_defaults(dataset_name)

    api_endpoint = _require_non_empty_text(
        dataset_config.get("api_endpoint", dataset_defaults.api_endpoint),
        f"{dataset_name}.api_endpoint",
    )
    if not api_endpoint.startswith("/"):
        api_endpoint = f"/{api_endpoint}"

    json_name = _require_non_empty_text(
        dataset_config.get("json_name", dataset_defaults.json_name),
        f"{dataset_name}.json_name",
    )
    table_name = _require_non_empty_text(
        dataset_config.get("table_name", dataset_defaults.table_name),
        f"{dataset_name}.table_name",
    )
    schema_value = _require_non_empty_text(
        dataset_config.get("schema_path", dataset_defaults.schema_path),
        f"{dataset_name}.schema_path",
    )
    source_dir = _resolve_path(
        project_root,
        str(system_config.get("source_dir", "")),
        "Source",
    )

    return DatasetConfig(
        name=dataset_name,
        config_path=resolved_config_path,
        project_root=project_root,
        api_endpoint=api_endpoint,
        api_url=f"https://openapi.twse.com.tw/v1{api_endpoint}",
        schema_path=_resolve_path(project_root, schema_value, dataset_defaults.schema_path),
        table_name=table_name,
        json_name=json_name,
        json_path=source_dir / json_name,
    )


def validate_config(config_path: Path | None = None, dataset_name: str | None = None) -> None:
    resolved_config_path = _resolve_config_path(config_path)

    try:
        get_raw_config(resolved_config_path)
        system_config = get_system_config(resolved_config_path)
    except Exception as exc:
        raise ConfigValidationError(
            f"config 驗證失敗: {resolved_config_path}: {exc}"
        ) from exc

    if system_config.db_driver != "sqlite":
        raise ConfigValidationError(
            f"config 驗證失敗: db_driver 目前只支援 sqlite，收到 {system_config.db_driver}"
        )
    if system_config.log_retention_days < 0:
        raise ConfigValidationError(
            "config 驗證失敗: system.log_retention_days 不可小於 0"
        )

    registry = _load_dataset_defaults_registry()
    target_datasets = (dataset_name,) if dataset_name else tuple(registry)
    for current_dataset in target_datasets:
        try:
            dataset = get_dataset_config(current_dataset, resolved_config_path)
        except Exception as exc:
            raise ConfigValidationError(
                f"config 驗證失敗: dataset={current_dataset}: {exc}"
            ) from exc

        if not dataset.schema_path.is_file():
            raise ConfigValidationError(
                f"config 驗證失敗: dataset={current_dataset}: schema 不存在 {dataset.schema_path}"
            )


def get_dataset_json_path(dataset_name: str, config_path: Path | None = None) -> Path:
    validate_config(config_path, dataset_name)
    return get_dataset_config(dataset_name, config_path).json_path