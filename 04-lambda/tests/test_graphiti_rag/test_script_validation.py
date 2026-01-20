"""Tests for Graphiti RAG AI script validation."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from server.projects.graphiti_rag.config import config as graphiti_config
from server.projects.graphiti_rag.tools import validate_ai_script

from tests.conftest import MockRunContext


@pytest.mark.asyncio
async def test_validate_ai_script(mock_graphiti_rag_deps):
    """Test AI script validation."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    script_path = "/path/to/script.py"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock validators
        with patch("server.projects.graphiti_rag.tools.AIScriptAnalyzer") as mock_analyzer_class:
            with patch(
                "server.projects.graphiti_rag.tools.KnowledgeGraphValidator"
            ) as mock_validator_class:
                with patch(
                    "server.projects.graphiti_rag.tools.HallucinationReporter"
                ) as mock_reporter_class:
                    # Mock analyzer
                    mock_analysis = Mock()
                    mock_analysis.imports = ["os", "sys"]
                    mock_analysis.classes = ["User"]
                    mock_analysis.methods = ["authenticate"]
                    mock_analysis.functions = ["main"]

                    mock_analyzer = Mock()
                    mock_analyzer.analyze_script = Mock(return_value=mock_analysis)
                    mock_analyzer_class.return_value = mock_analyzer

                    # Mock validator
                    mock_validation = Mock()
                    mock_validation.overall_confidence = 0.95
                    mock_validation.hallucinations = []

                    mock_validator = AsyncMock()
                    mock_validator.initialize = AsyncMock()
                    mock_validator.validate_script = AsyncMock(return_value=mock_validation)
                    mock_validator.close = AsyncMock()
                    mock_validator_class.return_value = mock_validator

                    # Mock reporter
                    mock_reporter = Mock()
                    mock_reporter.generate_comprehensive_report = Mock(
                        return_value={
                            "validation_summary": "All validations passed",
                            "hallucinations_detected": [],
                            "recommendations": [],
                        }
                    )
                    mock_reporter_class.return_value = mock_reporter

                    # Execute
                    result = await validate_ai_script(ctx, script_path)

                    # Assert
                    assert result["success"] is True
                    assert result["overall_confidence"] > 0.9
                    assert len(result["hallucinations_detected"]) == 0


@pytest.mark.asyncio
async def test_detect_hallucinations(mock_graphiti_rag_deps):
    """Test hallucination detection."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    script_path = "/path/to/script.py"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock validators with hallucinations
        with patch("server.projects.graphiti_rag.tools.AIScriptAnalyzer") as mock_analyzer_class:
            with patch(
                "server.projects.graphiti_rag.tools.KnowledgeGraphValidator"
            ) as mock_validator_class:
                with patch(
                    "server.projects.graphiti_rag.tools.HallucinationReporter"
                ) as mock_reporter_class:
                    # Mock analyzer
                    mock_analysis = Mock()
                    mock_analysis.imports = ["nonexistent_module"]
                    mock_analysis.classes = ["NonExistentClass"]
                    mock_analysis.methods = ["non_existent_method"]
                    mock_analysis.functions = []

                    mock_analyzer = Mock()
                    mock_analyzer.analyze_script = Mock(return_value=mock_analysis)
                    mock_analyzer_class.return_value = mock_analyzer

                    # Mock validator with hallucinations
                    mock_validation = Mock()
                    mock_validation.overall_confidence = 0.3
                    mock_validation.hallucinations = [
                        {
                            "type": "import",
                            "name": "nonexistent_module",
                            "reason": "Not found in knowledge graph",
                        },
                        {
                            "type": "class",
                            "name": "NonExistentClass",
                            "reason": "Not found in knowledge graph",
                        },
                    ]

                    mock_validator = AsyncMock()
                    mock_validator.initialize = AsyncMock()
                    mock_validator.validate_script = AsyncMock(return_value=mock_validation)
                    mock_validator.close = AsyncMock()
                    mock_validator_class.return_value = mock_validator

                    # Mock reporter
                    mock_reporter = Mock()
                    mock_reporter.generate_comprehensive_report = Mock(
                        return_value={
                            "validation_summary": "Hallucinations detected",
                            "hallucinations_detected": [
                                {"type": "import", "name": "nonexistent_module"}
                            ],
                            "recommendations": ["Remove nonexistent_module import"],
                        }
                    )
                    mock_reporter_class.return_value = mock_reporter

                    # Execute
                    result = await validate_ai_script(ctx, script_path)

                    # Assert
                    assert result["success"] is True
                    assert len(result["hallucinations_detected"]) > 0
                    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_validate_imports(mock_graphiti_rag_deps):
    """Test import validation."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    script_path = "/path/to/script.py"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock validators
        with patch("server.projects.graphiti_rag.tools.AIScriptAnalyzer") as mock_analyzer_class:
            with patch(
                "server.projects.graphiti_rag.tools.KnowledgeGraphValidator"
            ) as mock_validator_class:
                with patch(
                    "server.projects.graphiti_rag.tools.HallucinationReporter"
                ) as mock_reporter_class:
                    # Mock analyzer
                    mock_analysis = Mock()
                    mock_analysis.imports = ["os", "sys", "json"]
                    mock_analysis.classes = []
                    mock_analysis.methods = []
                    mock_analysis.functions = []

                    mock_analyzer = Mock()
                    mock_analyzer.analyze_script = Mock(return_value=mock_analysis)
                    mock_analyzer_class.return_value = mock_analyzer

                    # Mock validator
                    mock_validation = Mock()
                    mock_validation.overall_confidence = 1.0
                    mock_validation.hallucinations = []

                    mock_validator = AsyncMock()
                    mock_validator.initialize = AsyncMock()
                    mock_validator.validate_script = AsyncMock(return_value=mock_validation)
                    mock_validator.close = AsyncMock()
                    mock_validator_class.return_value = mock_validator

                    # Mock reporter
                    mock_reporter = Mock()
                    mock_reporter.generate_comprehensive_report = Mock(
                        return_value={
                            "validation_summary": "All imports valid",
                            "hallucinations_detected": [],
                            "recommendations": [],
                        }
                    )
                    mock_reporter_class.return_value = mock_reporter

                    # Execute
                    result = await validate_ai_script(ctx, script_path)

                    # Assert
                    assert result["success"] is True
                    assert result["overall_confidence"] == 1.0


@pytest.mark.asyncio
async def test_validate_method_calls(mock_graphiti_rag_deps):
    """Test method call validation."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    script_path = "/path/to/script.py"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock validators
        with patch("server.projects.graphiti_rag.tools.AIScriptAnalyzer") as mock_analyzer_class:
            with patch(
                "server.projects.graphiti_rag.tools.KnowledgeGraphValidator"
            ) as mock_validator_class:
                with patch(
                    "server.projects.graphiti_rag.tools.HallucinationReporter"
                ) as mock_reporter_class:
                    # Mock analyzer
                    mock_analysis = Mock()
                    mock_analysis.imports = []
                    mock_analysis.classes = ["User"]
                    mock_analysis.methods = ["authenticate", "logout"]
                    mock_analysis.functions = []

                    mock_analyzer = Mock()
                    mock_analyzer.analyze_script = Mock(return_value=mock_analysis)
                    mock_analyzer_class.return_value = mock_analyzer

                    # Mock validator
                    mock_validation = Mock()
                    mock_validation.overall_confidence = 0.9
                    mock_validation.hallucinations = []

                    mock_validator = AsyncMock()
                    mock_validator.initialize = AsyncMock()
                    mock_validator.validate_script = AsyncMock(return_value=mock_validation)
                    mock_validator.close = AsyncMock()
                    mock_validator_class.return_value = mock_validator

                    # Mock reporter
                    mock_reporter = Mock()
                    mock_reporter.generate_comprehensive_report = Mock(
                        return_value={
                            "validation_summary": "All method calls valid",
                            "hallucinations_detected": [],
                            "recommendations": [],
                        }
                    )
                    mock_reporter_class.return_value = mock_reporter

                    # Execute
                    result = await validate_ai_script(ctx, script_path)

                    # Assert
                    assert result["success"] is True
                    assert result["overall_confidence"] >= 0.9
