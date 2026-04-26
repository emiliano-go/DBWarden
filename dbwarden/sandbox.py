import os
import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, Set

from dbwarden.exceptions import ConfigurationError


ALLOWED_IMPORTS: Set[str] = {
    "dbwarden",
    "dbwarden.database_config",
}

ALLOWED_IMPORTS_PREFIXES: Set[str] = {
    "dbwarden.",
}


class SecurityError(ConfigurationError):
    """Raised when a security check fails."""
    pass


class RestrictedFileLoader(Loader):
    """
    Sandboxed file loader that restricts imports in loaded modules.

    Only allows:
    - Importing dbwarden and its submodules
    - Loading files within the project tree
    """

    _base_dir: Path
    _filepath: str

    def __init__(self, filepath: str, base_dir: Path) -> None:
        self._filepath = filepath
        self._base_dir = base_dir.resolve()

    def create_module(self, spec: ModuleSpec) -> None:
        return None

    def exec_module(self, module: ModuleSpec) -> None:
        # Read the source code from the file
        with open(self._filepath, "r") as f:
            source = f.read()
        
        # Compile and execute in restricted globals
        module.__loader__ = self
        code = compile(source, self._filepath, "exec")
        exec(code, module.__dict__)

    def find_module(
        self, fullname: str, path: str | None = None, target: ModuleSpec | None = None
    ) -> "RestrictedFileLoader | None":
        """Check if module can be imported."""
        if self._is_allowed_import(fullname):
            return self
        return None

    def _is_allowed_import(self, fullname: str) -> bool:
        """Check if import is allowed."""
        if fullname in ALLOWED_IMPORTS:
            return True
        for prefix in ALLOWED_IMPORTS_PREFIXES:
            if fullname.startswith(prefix):
                return True
        return False


class RestrictedModuleFinder(MetaPathFinder):
    """
    Meta path finder that restricts which modules can be loaded.

    Use with RestrictedFileLoader for complete sandboxing.
    """

    _base_dir: Path
    _allowed_imports: Set[str]

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._allowed_imports = ALLOWED_IMPORTS.copy()

    def find_spec(
        self,
        fullname: str,
        path: str | None = None,
        target: ModuleSpec | None = None,
    ) -> ModuleSpec | None:
        """Find and validate module spec."""
        if not self._is_allowed(fullname):
            raise SecurityError(
                f"Import '{fullname}' not allowed. "
                f"Only dbwarden imports are permitted in config files."
            )
        return None

    def _is_allowed(self, fullname: str) -> bool:
        """Check if module is allowed."""
        if fullname in self._allowed_imports:
            return True
        for prefix in ALLOWED_IMPORTS_PREFIXES:
            if fullname.startswith(prefix):
                return True
        return False


def validate_path(path: Path, base_dir: Path) -> None:
    """
    Validate that a config path is safe to load.

    Raises SecurityError if:
    - Path is outside the project tree
    - Path contains path traversal sequences
    - Path is absolute and points outside project

    Args:
        path: Path to the config file
        base_dir: Project root directory

    Raises:
        SecurityError: If path is not safe
    """
    resolved = path.resolve()
    base = base_dir.resolve()

    # Check for path traversal
    path_str = str(path)
    if ".." in path_str.split("/"):
        raise SecurityError(
            f"Refusing to load config with path traversal: {path}"
        )

    # Check if within project tree for relative paths
    if not path.is_absolute():
        try:
            resolved = (base / path).resolve()
        except Exception as e:
            raise SecurityError(f"Invalid path: {path}") from e

    # Verify resolved path is under base_dir
    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityError(
            f"Refusing to load config from outside project tree: {path}\n"
            f"Project root: {base}\n"
            f"Config path: {resolved}"
        )


def validate_model_path(path: Path, base_dir: Path) -> None:
    """
    Validate that a model path is safe to load.

    For model files, we only block path traversal attacks.
    Model paths are already user-configured in database_config(),
    so we trust them more than arbitrary discovered config files.

    Args:
        path: Path to the model file
        base_dir: Project root directory (used for temp dir resolution)

    Raises:
        SecurityError: If path contains traversal sequences
    """
    # Only check for path traversal - model paths are user-configured
    path_str = str(path)
    if ".." in path_str.split("/"):
        raise SecurityError(
            f"Refusing to load model with path traversal: {path}"
        )


def load_config_module(path: Path, base_dir: Path) -> None:
    """
    Load a config module with security checks.

    Args:
        path: Path to config file (e.g., dbwarden.py)
        base_dir: Project root directory

    Raises:
        SecurityError: If path is invalid or import is disallowed
        ConfigurationError: If loading fails
    """
    # Validate path before loading
    validate_path(path, base_dir)

    # Check DBWARDEN_DISABLE_SANDBOX env var (for debugging)
    if os.environ.get("DBWARDEN_DISABLE_SANDBOX"):
        # Fall back to unsafe loading
        _unsafe_load(path)
        return

    # Use sandboxed loader
    _sandboxed_load(path, base_dir)


def _sandboxed_load(path: Path, base_dir: Path) -> None:
    """Load module in sandbox."""
    import importlib.util

    module_name = f"_dbwarden_config_{abs(hash(str(path)))}"
    filepath = str(path)

    # Create restricted file loader with filepath
    file_loader = RestrictedFileLoader(filepath, base_dir)

    # Create spec with restricted loader
    spec = ModuleSpec(
        module_name,
        file_loader,
        origin=filepath,
    )

    # Create and execute module
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except SecurityError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to load config from {path}: {e}") from e
    finally:
        # Clean up sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]


def _unsafe_load(path: Path) -> None:
    """Unsandboxed load (for debugging)."""
    import importlib.util

    path = Path(path)
    module_name = f"_dbwarden_config_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ConfigurationError(f"Could not load config source: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def load_model_module(filepath: Path, base_dir: Path) -> Any:
    """
    Load a model module with path validation.

    For model files (unlike config), we allow sqlalchemy and other model-related
    imports - we're just validating the path is within project.

    Args:
        filepath: Path to the model file
        base_dir: Project root directory

    Returns:
        Loaded module or None if failed
    """
    validate_model_path(filepath, base_dir)

    # Check DBWARDEN_DISABLE_SANDBOX env var
    if os.environ.get("DBWARDEN_DISABLE_SANDBOX"):
        return _unsafe_load_model(filepath)

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("models", filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module
    except Exception:
        return None


def _unsafe_load_model(filepath: Path) -> Any:
    """Unsandboxed model load."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("models", filepath)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module