"""API Controller for Spec-to-Pack Studio."""

from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from .app import StudioApp
from .artifacts import ArtifactIndex
from .types import Dials, PackType, SourceSpec


# API Models following the class diagram
class RunInfo(BaseModel):
    """Information about a generation run."""
    run_id: UUID
    status: str
    artifacts_count: int
    output_dir: str


class ValidationReport(BaseModel):
    """Validation report for API responses."""
    valid: bool
    errors: list
    spec_summary: dict[str, Any]


# API Controller following the class diagram pattern
class ApiController:
    """API Controller following the class diagram pattern."""

    def __init__(self):
        """Initialize API controller with StudioApp."""
        self.app = StudioApp()

    def POST_generate(self, payload: dict[str, Any]) -> RunInfo:
        """Generate a document pack from API payload."""
        try:
            # Extract parameters from payload
            spec_data = payload.get("spec")
            pack_type = PackType(payload.get("pack", "balanced"))
            out_dir = Path(payload.get("out_dir", "./out"))
            offline = payload.get("offline", False)
            dials_data = payload.get("dials", {})

            # Create spec and dials objects
            spec = SourceSpec(**spec_data)
            dials = Dials(**dials_data) if dials_data else Dials()

            # Generate pack
            artifact_index = self.app.generate(
                spec=spec,
                pack=pack_type,
                out_dir=out_dir,
                offline=offline,
                dials=dials
            )

            return RunInfo(
                run_id=artifact_index.run_id,
                status="completed",
                artifacts_count=len(artifact_index.artifacts),
                output_dir=str(out_dir)
            )

        except Exception as e:
            return RunInfo(
                run_id=UUID("00000000-0000-0000-0000-000000000000"),
                status=f"failed: {str(e)}",
                artifacts_count=0,
                output_dir=""
            )

    def POST_validate(self, spec: SourceSpec) -> ValidationReport:
        """Validate a source spec."""
        try:
            result = self.app.validate(spec)

            return ValidationReport(
                valid=result.ok,
                errors=[{"pointer": err.json_pointer, "message": err.message}
                       for err in result.errors],
                spec_summary={
                    "name": spec.meta.name,
                    "version": spec.meta.version,
                    "problem": spec.problem.statement[:100] + "..." if len(spec.problem.statement) > 100 else spec.problem.statement
                }
            )

        except Exception as e:
            return ValidationReport(
                valid=False,
                errors=[{"pointer": "/", "message": f"Validation error: {str(e)}"}],
                spec_summary={}
            )

    def GET_runs(self, run_id: UUID) -> ArtifactIndex | None:
        """Get run information by ID."""
        # TODO: Implement run storage/retrieval
        # For now, return None as this would require a database
        return None


# Global controller instance for API framework integration
api_controller = ApiController()
