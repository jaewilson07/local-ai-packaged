#!/usr/bin/env python3
"""Compliance verification script for Service vs Capability Architecture.

This script verifies that all projects comply with the architecture patterns
defined in the PRD. It checks file structure, code patterns, and generates
compliance reports.
"""

import argparse
import ast
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ComplianceViolation:
    """Represents a single compliance violation."""

    project: str
    file: str
    line: int
    violation_type: str
    message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ProjectCompliance:
    """Compliance status for a single project."""

    project_name: str
    is_compliant: bool
    violations: list[ComplianceViolation] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    compliance_score: float = 0.0


@dataclass
class ComplianceReport:
    """Overall compliance report."""

    total_projects: int
    compliant_projects: int
    partially_compliant_projects: int
    non_compliant_projects: int
    projects: dict[str, ProjectCompliance] = field(default_factory=dict)
    violations_by_type: dict[str, int] = field(default_factory=dict)


class ComplianceChecker:
    """Checks project compliance with architecture patterns."""

    REQUIRED_FILES = ["config.py", "dependencies.py", "tools.py", "agent.py", "models.py"]
    OPTIONAL_FILES = ["README.md", "prompts.py"]

    def __init__(self, projects_dir: Path):
        """Initialize checker with projects directory."""
        self.projects_dir = projects_dir
        self.report = ComplianceReport(
            total_projects=0,
            compliant_projects=0,
            partially_compliant_projects=0,
            non_compliant_projects=0,
        )

    def check_all_projects(self, exclude: list[str] | None = None) -> ComplianceReport:
        """Check compliance for all projects."""
        exclude = exclude or []
        projects = [
            d
            for d in self.projects_dir.iterdir()
            if d.is_dir()
            and not d.name.startswith("_")
            and d.name not in exclude
            and (d / "__init__.py").exists()
        ]

        self.report.total_projects = len(projects)

        for project_dir in sorted(projects):
            project_name = project_dir.name
            logger.info(f"Checking project: {project_name}")
            project_compliance = self.check_project(project_dir, project_name)
            self.report.projects[project_name] = project_compliance

            # Update statistics
            if project_compliance.is_compliant:
                self.report.compliant_projects += 1
            elif project_compliance.compliance_score >= 0.7:
                self.report.partially_compliant_projects += 1
            else:
                self.report.non_compliant_projects += 1

            # Count violations by type
            for violation in project_compliance.violations:
                self.report.violations_by_type[violation.violation_type] = (
                    self.report.violations_by_type.get(violation.violation_type, 0) + 1
                )

        return self.report

    def check_project(self, project_dir: Path, project_name: str) -> ProjectCompliance:
        """Check compliance for a single project."""
        compliance = ProjectCompliance(project_name=project_name, is_compliant=True)

        # Check file structure
        self._check_file_structure(project_dir, compliance)

        # Check dependencies pattern
        self._check_dependencies_pattern(project_dir, compliance)

        # Check tools pattern
        self._check_tools_pattern(project_dir, compliance)

        # Check agent pattern
        self._check_agent_pattern(project_dir, compliance)

        # Check REST pattern (if API file exists)
        self._check_rest_pattern(project_dir, compliance)

        # Calculate compliance score
        total_checks = len(self.REQUIRED_FILES) + 4  # files + 4 pattern checks
        passed_checks = (len(self.REQUIRED_FILES) - len(compliance.missing_files)) + (
            4 - len(compliance.violations)
        )
        compliance.compliance_score = passed_checks / total_checks if total_checks > 0 else 0.0
        compliance.is_compliant = (
            compliance.compliance_score == 1.0 and len(compliance.violations) == 0
        )

        return compliance

    def _check_file_structure(self, project_dir: Path, compliance: ProjectCompliance) -> None:
        """Check if required files exist."""
        for required_file in self.REQUIRED_FILES:
            file_path = project_dir / required_file
            if not file_path.exists():
                compliance.missing_files.append(required_file)
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file=required_file,
                        line=0,
                        violation_type="missing_file",
                        message=f"Required file {required_file} is missing",
                        severity="error",
                    )
                )

    def _check_dependencies_pattern(self, project_dir: Path, compliance: ProjectCompliance) -> None:
        """Check dependencies.py pattern."""
        deps_file = project_dir / "dependencies.py"
        if not deps_file.exists():
            return

        try:
            with open(deps_file, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(deps_file))

            # Check for BaseDependencies inheritance
            has_base_deps = False
            has_initialize = False
            has_cleanup = False
            has_from_settings = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check inheritance
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseDependencies":
                            has_base_deps = True
                        elif isinstance(base, ast.Attribute):
                            if base.attr == "BaseDependencies":
                                has_base_deps = True

                    # Check methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name == "initialize":
                                has_initialize = True
                            elif item.name == "cleanup":
                                has_cleanup = True
                        elif isinstance(item, ast.FunctionDef) and any(
                            isinstance(d, ast.Name) and d.id == "classmethod"
                            for d in (
                                item.decorator_list if hasattr(item, "decorator_list") else []
                            )
                        ):
                            if item.name == "from_settings":
                                has_from_settings = True

            if not has_base_deps:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file="dependencies.py",
                        line=0,
                        violation_type="dependencies_inheritance",
                        message="Dependencies class does not inherit from BaseDependencies",
                        severity="error",
                    )
                )

            if not has_initialize:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file="dependencies.py",
                        line=0,
                        violation_type="dependencies_initialize",
                        message="Dependencies class missing initialize() method",
                        severity="error",
                    )
                )

            if not has_cleanup:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file="dependencies.py",
                        line=0,
                        violation_type="dependencies_cleanup",
                        message="Dependencies class missing cleanup() method",
                        severity="error",
                    )
                )

        except Exception as e:
            compliance.violations.append(
                ComplianceViolation(
                    project=compliance.project_name,
                    file="dependencies.py",
                    line=0,
                    violation_type="dependencies_parse_error",
                    message=f"Error parsing dependencies.py: {e}",
                    severity="error",
                )
            )

    def _check_tools_pattern(self, project_dir: Path, compliance: ProjectCompliance) -> None:
        """Check tools.py pattern."""
        tools_file = project_dir / "tools.py"
        if not tools_file.exists():
            return

        try:
            with open(tools_file, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(tools_file))

            # Check function signatures
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if node.name.startswith("_"):
                        continue

                    # Check if first parameter is RunContext
                    if node.args.args:
                        first_param = node.args.args[0]
                        if isinstance(first_param.annotation, ast.Subscript):
                            # Check for RunContext[...]
                            if isinstance(first_param.annotation.value, ast.Name):
                                if first_param.annotation.value.id != "RunContext":
                                    compliance.violations.append(
                                        ComplianceViolation(
                                            project=compliance.project_name,
                                            file="tools.py",
                                            line=node.lineno,
                                            violation_type="tools_signature",
                                            message=f"Function {node.name} first parameter should be RunContext[Dependencies]",
                                            severity="error",
                                        )
                                    )

        except Exception as e:
            compliance.violations.append(
                ComplianceViolation(
                    project=compliance.project_name,
                    file="tools.py",
                    line=0,
                    violation_type="tools_parse_error",
                    message=f"Error parsing tools.py: {e}",
                    severity="error",
                )
            )

    def _check_agent_pattern(self, project_dir: Path, compliance: ProjectCompliance) -> None:
        """Check agent.py pattern."""
        agent_file = project_dir / "agent.py"
        if not agent_file.exists():
            return

        try:
            with open(agent_file, encoding="utf-8") as f:
                content = f.read()

            # Check for agent definition
            if "Agent(" not in content and "agent = Agent" not in content:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file="agent.py",
                        line=0,
                        violation_type="agent_definition",
                        message="agent.py should define an Agent instance",
                        severity="warning",
                    )
                )

            # Check for agent tools
            if "@agent.tool" not in content and "@" not in content:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file="agent.py",
                        line=0,
                        violation_type="agent_tools",
                        message="agent.py should define agent tools",
                        severity="warning",
                    )
                )

        except Exception as e:
            compliance.violations.append(
                ComplianceViolation(
                    project=compliance.project_name,
                    file="agent.py",
                    line=0,
                    violation_type="agent_parse_error",
                    message=f"Error reading agent.py: {e}",
                    severity="error",
                )
            )

    def _check_rest_pattern(self, project_dir: Path, compliance: ProjectCompliance) -> None:
        """Check REST API pattern (if API file exists)."""
        # Check if corresponding API file exists
        api_dir = project_dir.parent.parent / "api"
        project_name = project_dir.name
        api_file = api_dir / f"{project_name}.py"

        if not api_file.exists():
            # Some projects might use router.py instead
            router_file = project_dir / "router.py"
            if router_file.exists():
                api_file = router_file
            else:
                return  # No API file to check

        try:
            with open(api_file, encoding="utf-8") as f:
                content = f.read()

            # Check for create_run_context usage
            if "create_run_context" not in content:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file=api_file.name,
                        line=0,
                        violation_type="rest_pattern",
                        message=f"{api_file.name} should use create_run_context() helper",
                        severity="warning",
                    )
                )

            # Check for tools.py imports
            if f"from server.projects.{project_name}.tools import" not in content:
                compliance.violations.append(
                    ComplianceViolation(
                        project=compliance.project_name,
                        file=api_file.name,
                        line=0,
                        violation_type="rest_tools_import",
                        message=f"{api_file.name} should import from tools.py",
                        severity="warning",
                    )
                )

        except Exception as e:
            compliance.violations.append(
                ComplianceViolation(
                    project=compliance.project_name,
                    file=api_file.name,
                    line=0,
                    violation_type="rest_parse_error",
                    message=f"Error reading {api_file.name}: {e}",
                    severity="error",
                )
            )


def generate_markdown_report(report: ComplianceReport) -> str:
    """Generate markdown compliance report."""
    lines = []
    lines.append("# Architecture Compliance Report\n")
    lines.append(f"**Generated**: {Path(__file__).stat().st_mtime}\n")
    lines.append("## Summary\n")
    lines.append(f"- **Total Projects**: {report.total_projects}")
    lines.append(f"- **Fully Compliant**: {report.compliant_projects}")
    lines.append(f"- **Partially Compliant**: {report.partially_compliant_projects}")
    lines.append(f"- **Non-Compliant**: {report.non_compliant_projects}\n")

    if report.violations_by_type:
        lines.append("## Violations by Type\n")
        for violation_type, count in sorted(report.violations_by_type.items()):
            lines.append(f"- **{violation_type}**: {count}")

    lines.append("\n## Project Details\n")

    for project_name, project_compliance in sorted(report.projects.items()):
        status = "✅ Compliant" if project_compliance.is_compliant else "⚠️ Non-Compliant"
        if project_compliance.compliance_score >= 0.7 and not project_compliance.is_compliant:
            status = "⚠️ Partially Compliant"

        lines.append(f"### {project_name} - {status}")
        lines.append(f"**Compliance Score**: {project_compliance.compliance_score:.1%}\n")

        if project_compliance.missing_files:
            lines.append("**Missing Files**:")
            for file in project_compliance.missing_files:
                lines.append(f"- {file}")

        if project_compliance.violations:
            lines.append("\n**Violations**:")
            for violation in project_compliance.violations:
                lines.append(
                    f"- **{violation.violation_type}** ({violation.severity}): {violation.message}"
                )
                if violation.line > 0:
                    lines.append(f"  - File: {violation.file}, Line: {violation.line}")

        lines.append("")

    return "\n".join(lines)


def generate_json_report(report: ComplianceReport) -> dict[str, Any]:
    """Generate JSON compliance report."""
    return {
        "summary": {
            "total_projects": report.total_projects,
            "compliant_projects": report.compliant_projects,
            "partially_compliant_projects": report.partially_compliant_projects,
            "non_compliant_projects": report.non_compliant_projects,
            "violations_by_type": report.violations_by_type,
        },
        "projects": {
            name: {
                "is_compliant": project.is_compliant,
                "compliance_score": project.compliance_score,
                "missing_files": project.missing_files,
                "violations": [
                    {
                        "file": v.file,
                        "line": v.line,
                        "violation_type": v.violation_type,
                        "message": v.message,
                        "severity": v.severity,
                    }
                    for v in project.violations
                ],
            }
            for name, project in report.projects.items()
        },
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify architecture compliance")
    parser.add_argument(
        "--project",
        type=str,
        help="Check specific project only",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any non-compliance",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Projects to exclude from verification",
    )

    args = parser.parse_args()

    # Find projects directory
    script_dir = Path(__file__).parent
    projects_dir = script_dir

    checker = ComplianceChecker(projects_dir)

    if args.project:
        # Check single project
        project_dir = projects_dir / args.project
        if not project_dir.exists():
            logger.error(f"Project {args.project} not found")
            sys.exit(1)
        report = ComplianceReport(0, 0, 0, 0)
        report.projects[args.project] = checker.check_project(project_dir, args.project)
        report.total_projects = 1
        if report.projects[args.project].is_compliant:
            report.compliant_projects = 1
        else:
            report.non_compliant_projects = 1
    else:
        # Check all projects
        report = checker.check_all_projects(exclude=args.exclude)

    # Generate output
    output_text = ""
    if args.format in ["json", "both"]:
        json_report = generate_json_report(report)
        output_text = json.dumps(json_report, indent=2)

    if args.format in ["markdown", "both"]:
        if args.format == "both":
            output_text += "\n\n" + "=" * 80 + "\n\n"
        output_text += generate_markdown_report(report)

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        logger.info(f"Report written to {args.output}")
    else:
        print(output_text)

    # Exit with error if strict mode and non-compliant
    if args.strict and report.non_compliant_projects > 0:
        logger.error(f"Strict mode: {report.non_compliant_projects} non-compliant projects found")
        sys.exit(1)

    if args.strict and report.partially_compliant_projects > 0:
        logger.warning(
            f"Strict mode: {report.partially_compliant_projects} partially compliant projects found"
        )


if __name__ == "__main__":
    main()
