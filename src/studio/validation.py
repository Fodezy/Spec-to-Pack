"""Schema validation components."""

import json
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import ValidationError as PydanticValidationError

from .types import SourceSpec, ValidationError, ValidationResult


class SchemaValidator:
    """Validates specs against JSON schemas."""

    def __init__(self, schema_dir: Path = None):
        """Initialize validator with schema directory."""
        if schema_dir is None:
            schema_dir = Path(__file__).parent.parent.parent / "schemas"
        self.schema_dir = schema_dir
        self._schemas = {}

    def _load_schema(self, schema_name: str) -> dict[str, Any]:
        """Load a JSON schema by name."""
        if schema_name not in self._schemas:
            schema_path = self.schema_dir / f"{schema_name}.schema.json"
            if schema_path.exists():
                with open(schema_path) as f:
                    self._schemas[schema_name] = json.load(f)
            else:
                # Return a minimal schema if file doesn't exist
                self._schemas[schema_name] = {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object"
                }
        return self._schemas[schema_name]

    def validate(self, spec: SourceSpec) -> ValidationResult:
        """Validate a source spec against its schema."""
        errors = []

        try:
            # First validate with Pydantic
            spec.model_validate(spec.model_dump())
        except PydanticValidationError as e:
            for error in e.errors():
                location = ".".join(str(loc) for loc in error["loc"])
                errors.append(ValidationError(
                    json_pointer=f"/{location.replace('.', '/')}",
                    message=error["msg"]
                ))

        # Additional JSON Schema validation
        try:
            schema = self._load_schema("source_spec")
            spec_dict = spec.model_dump()
            jsonschema.validate(spec_dict, schema)
        except jsonschema.ValidationError as e:
            # Build proper JSON pointer from absolute path
            pointer = "/" + "/".join(str(part) for part in e.absolute_path) if e.absolute_path else "/"
            errors.append(ValidationError(
                json_pointer=pointer,
                message=str(e.message)
            ))
        except Exception as e:
            errors.append(ValidationError(
                json_pointer="/",
                message=f"Schema validation failed: {str(e)}"
            ))

        return ValidationResult(
            ok=len(errors) == 0,
            errors=errors
        )
