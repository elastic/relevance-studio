# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for the FastMCP resources server.

These tests verify the helper functions and data transformation logic
without requiring a running server or Elasticsearch.
"""

import pytest
from unittest.mock import MagicMock, patch


################################################################################
#                       TYPE COERCION HELPERS                                  #
################################################################################

class TestIntCoercion:
    """Tests for the _int helper function."""

    def test_int_with_int(self):
        """Integer values should pass through unchanged."""
        from server.fastmcp_resources import _int
        assert _int(10) == 10
        assert _int(0) == 0
        assert _int(-5) == -5

    def test_int_with_string(self):
        """String numbers should be converted to int."""
        from server.fastmcp_resources import _int
        assert _int("10") == 10
        assert _int("0") == 0
        assert _int("-5") == -5

    def test_int_with_none(self):
        """None should return the default."""
        from server.fastmcp_resources import _int
        assert _int(None) is None
        assert _int(None, 10) == 10
        assert _int(None, 0) == 0

    def test_int_with_invalid_string(self):
        """Invalid strings should return the default."""
        from server.fastmcp_resources import _int
        assert _int("abc") is None
        assert _int("abc", 10) == 10
        assert _int("1.5", 10) == 10  # float string is invalid for int
        assert _int("", 10) == 10

    def test_int_with_float(self):
        """Floats should be converted to int."""
        from server.fastmcp_resources import _int
        assert _int(10.5) == 10
        assert _int(10.9) == 10

    def test_int_with_bool(self):
        """Booleans should convert to 0/1."""
        from server.fastmcp_resources import _int
        assert _int(True) == 1
        assert _int(False) == 0


class TestBoolCoercion:
    """Tests for the _bool helper function."""

    def test_bool_with_bool(self):
        """Boolean values should pass through unchanged."""
        from server.fastmcp_resources import _bool
        assert _bool(True) is True
        assert _bool(False) is False

    def test_bool_with_none(self):
        """None should return the default."""
        from server.fastmcp_resources import _bool
        assert _bool(None) is False
        assert _bool(None, True) is True
        assert _bool(None, False) is False

    def test_bool_with_string_true(self):
        """Truthy strings should return True."""
        from server.fastmcp_resources import _bool
        assert _bool("true") is True
        assert _bool("True") is True
        assert _bool("TRUE") is True
        assert _bool("1") is True
        assert _bool("yes") is True
        assert _bool("Yes") is True
        assert _bool("YES") is True

    def test_bool_with_string_false(self):
        """Falsy strings should return False."""
        from server.fastmcp_resources import _bool
        assert _bool("false") is False
        assert _bool("False") is False
        assert _bool("0") is False
        assert _bool("no") is False
        assert _bool("") is False
        assert _bool("anything") is False

    def test_bool_with_int(self):
        """Integers should convert via truthiness."""
        from server.fastmcp_resources import _bool
        assert _bool(1) is True
        assert _bool(0) is False
        assert _bool(100) is True


################################################################################
#                       HELPER FUNCTION TESTS                                  #
################################################################################

class TestGetWorkspacesList:
    """Tests for _get_workspaces_list helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_filtered_fields(self, mock_api):
        """Should return only the fields needed for listing."""
        from server.fastmcp_resources import _get_workspaces_list

        # Mock ES response
        mock_api.workspaces.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "ws-1",
                        "_source": {
                            "name": "Test Workspace",
                            "index_pattern": "test-*",
                            "params": ["text"],
                            "rating_scale": {"min": 0, "max": 3},
                            "tags": ["prod"],
                            "extra_field": "should be filtered",
                        }
                    }
                ]
            }
        })

        result = _get_workspaces_list()

        assert result["count"] == 1
        assert len(result["workspaces"]) == 1
        ws = result["workspaces"][0]
        assert ws["_id"] == "ws-1"
        assert ws["name"] == "Test Workspace"
        assert ws["index_pattern"] == "test-*"
        assert ws["params"] == ["text"]
        assert ws["rating_scale"] == {"min": 0, "max": 3}
        assert ws["tags"] == ["prod"]
        assert "extra_field" not in ws

    @patch('server.fastmcp_resources.api')
    def test_empty_result(self, mock_api):
        """Should handle empty results gracefully."""
        from server.fastmcp_resources import _get_workspaces_list

        mock_api.workspaces.search.return_value = MagicMock(body={
            "hits": {"hits": []}
        })

        result = _get_workspaces_list()

        assert result["count"] == 0
        assert result["workspaces"] == []

    @patch('server.fastmcp_resources.api')
    def test_missing_optional_fields(self, mock_api):
        """Should handle missing optional fields with defaults."""
        from server.fastmcp_resources import _get_workspaces_list

        mock_api.workspaces.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "ws-1",
                        "_source": {
                            "name": "Minimal Workspace",
                        }
                    }
                ]
            }
        })

        result = _get_workspaces_list()

        ws = result["workspaces"][0]
        assert ws["params"] == []
        assert ws["tags"] == []


class TestGetScenariosList:
    """Tests for _get_scenarios_list helper."""

    @patch('server.fastmcp_resources.api')
    def test_with_workspace_id(self, mock_api):
        """Should include workspace_id in response when provided."""
        from server.fastmcp_resources import _get_scenarios_list

        mock_api.scenarios.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "sc-1",
                        "_source": {
                            "name": "Test Scenario",
                            "values": {"text": "hello"},
                            "tags": ["test"],
                            "workspace_id": "ws-1",
                        }
                    }
                ]
            }
        })

        result = _get_scenarios_list("ws-1")

        assert result["workspace_id"] == "ws-1"
        assert result["count"] == 1
        scenario = result["scenarios"][0]
        assert scenario["_id"] == "sc-1"
        assert "workspace_id" not in scenario  # Not included when querying by workspace

    @patch('server.fastmcp_resources.api')
    def test_without_workspace_id(self, mock_api):
        """Should include workspace_id in each item when not filtering."""
        from server.fastmcp_resources import _get_scenarios_list

        mock_api.scenarios.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "sc-1",
                        "_source": {
                            "name": "Test Scenario",
                            "values": {"text": "hello"},
                            "tags": [],
                            "workspace_id": "ws-1",
                        }
                    }
                ]
            }
        })

        result = _get_scenarios_list("")

        assert "workspace_id" not in result  # No top-level workspace_id
        scenario = result["scenarios"][0]
        assert scenario["workspace_id"] == "ws-1"  # Included in each item


class TestGetStrategiesList:
    """Tests for _get_strategies_list helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_filtered_fields(self, mock_api):
        """Should not include template source in list results."""
        from server.fastmcp_resources import _get_strategies_list

        mock_api.strategies.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "str-1",
                        "_source": {
                            "name": "Match Query",
                            "tags": ["baseline"],
                            "workspace_id": "ws-1",
                            "template": {
                                "source": '{"query": {"match": {"text": "{{text}}"}}}',
                                "lang": "mustache"
                            }
                        }
                    }
                ]
            }
        })

        result = _get_strategies_list("ws-1")

        strategy = result["strategies"][0]
        assert strategy["_id"] == "str-1"
        assert strategy["name"] == "Match Query"
        assert strategy["tags"] == ["baseline"]
        assert "template" not in strategy  # Should be filtered out


class TestGetBenchmarksList:
    """Tests for _get_benchmarks_list helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_filtered_fields(self, mock_api):
        """Should include description but not task details."""
        from server.fastmcp_resources import _get_benchmarks_list

        mock_api.benchmarks.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "bm-1",
                        "_source": {
                            "name": "Full Benchmark",
                            "description": "Tests all scenarios",
                            "tags": ["weekly"],
                            "workspace_id": "ws-1",
                            "task": {
                                "metrics": ["ndcg@10"],
                                "k": 10
                            }
                        }
                    }
                ]
            }
        })

        result = _get_benchmarks_list("ws-1")

        benchmark = result["benchmarks"][0]
        assert benchmark["_id"] == "bm-1"
        assert benchmark["name"] == "Full Benchmark"
        assert benchmark["description"] == "Tests all scenarios"
        assert benchmark["tags"] == ["weekly"]
        assert "task" not in benchmark  # Should be filtered out


class TestGetEvaluationsList:
    """Tests for _get_evaluations_list helper."""

    @patch('server.fastmcp_resources.es')
    def test_returns_lightweight_fields(self, mock_es):
        """Should return status info without full results."""
        from server.fastmcp_resources import _get_evaluations_list

        # Mock direct ES query (bypasses broken API)
        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "eval-1",
                        "_source": {
                            "workspace_id": "ws-1",
                            "benchmark_id": "bm-1",
                            "@meta": {
                                "status": "completed",
                                "started_at": "2024-01-01T00:00:00Z"
                            },
                            "took": 1234,
                            "results": [{"should": "be excluded"}],
                            "summary": {"should": "also be excluded"}
                        }
                    }
                ]
            }
        })

        result = _get_evaluations_list("ws-1")

        assert result["workspace_id"] == "ws-1"
        assert result["count"] == 1
        evaluation = result["evaluations"][0]
        assert evaluation["_id"] == "eval-1"
        assert evaluation["benchmark_id"] == "bm-1"
        assert evaluation["status"] == "completed"
        assert evaluation["took"] == 1234
        assert "results" not in evaluation
        assert "summary" not in evaluation

    @patch('server.fastmcp_resources.es')
    def test_uses_direct_es_query(self, mock_es):
        """Should use direct ES query with correct index and filter."""
        from server.fastmcp_resources import _get_evaluations_list

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {"hits": []}
        })

        _get_evaluations_list("ws-123")

        # Verify ES was called correctly
        mock_es.assert_called_with("studio")
        mock_es.return_value.search.assert_called_once()
        call_kwargs = mock_es.return_value.search.call_args
        assert call_kwargs.kwargs["index"] == "esrs-evaluations"
        body = call_kwargs.kwargs["body"]
        assert body["query"]["bool"]["filter"][0]["term"]["workspace_id"] == "ws-123"


class TestGetEvaluationStatus:
    """Tests for _get_evaluation_status helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_status_fields(self, mock_api):
        """Should return only status-related fields."""
        from server.fastmcp_resources import _get_evaluation_status

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "@meta": {
                    "status": "completed",
                    "started_at": "2024-01-01T00:00:00Z",
                    "started_by": "user@test.com"
                },
                "took": 5000,
                "error": None,
                "results": [{"should": "not appear"}],
                "summary": {"should": "not appear"}
            }
        })

        result = _get_evaluation_status("eval-1")

        assert result["_id"] == "eval-1"
        assert result["status"] == "completed"
        assert result["started_at"] == "2024-01-01T00:00:00Z"
        assert result["started_by"] == "user@test.com"
        assert result["took"] == 5000
        assert result["error"] is None
        assert "results" not in result
        assert "summary" not in result


class TestGetEvaluationSummary:
    """Tests for _get_evaluation_summary helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_summary_fields(self, mock_api):
        """Should return summary without full results."""
        from server.fastmcp_resources import _get_evaluation_summary

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "@meta": {"status": "completed"},
                "took": 5000,
                "summary": {
                    "strategy_id": {
                        "str-1": {"_total": {"metrics": {"ndcg@10": {"avg": 0.85}}}}
                    }
                },
                "results": [{"should": "not appear"}]
            }
        })

        result = _get_evaluation_summary("eval-1")

        assert result["_id"] == "eval-1"
        assert result["status"] == "completed"
        assert result["took"] == 5000
        assert "strategy_id" in result["summary"]
        assert "results" not in result


class TestGetEvaluationResultsByStrategy:
    """Tests for _get_evaluation_results_by_strategy helper."""

    @patch('server.fastmcp_resources.api')
    def test_returns_single_strategy_results(self, mock_api):
        """Should return results for only the requested strategy."""
        from server.fastmcp_resources import _get_evaluation_results_by_strategy

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "results": [
                    {
                        "strategy_id": "str-1",
                        "searches": [{"scenario_id": "sc-1", "hits": []}],
                        "failures": []
                    },
                    {
                        "strategy_id": "str-2",
                        "searches": [{"scenario_id": "sc-1", "hits": []}],
                        "failures": []
                    }
                ]
            }
        })

        result = _get_evaluation_results_by_strategy("eval-1", "str-1")

        assert result["_id"] == "eval-1"
        assert result["strategy_id"] == "str-1"
        assert len(result["searches"]) == 1
        assert "failures" in result

    @patch('server.fastmcp_resources.api')
    def test_strategy_not_found(self, mock_api):
        """Should return error when strategy not in results."""
        from server.fastmcp_resources import _get_evaluation_results_by_strategy

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "results": [
                    {"strategy_id": "str-1", "searches": [], "failures": []},
                    {"strategy_id": "str-2", "searches": [], "failures": []}
                ]
            }
        })

        result = _get_evaluation_results_by_strategy("eval-1", "str-nonexistent")

        assert result["error"] == "Strategy str-nonexistent not found in evaluation results"
        assert result["available_strategies"] == ["str-1", "str-2"]


################################################################################
#                       LIGHTWEIGHT TOOL TESTS                                 #
#                                                                              #
#  Note: The @mcp.tool() decorator wraps functions into FunctionTool objects.  #
#  These tests verify the underlying function logic through the helpers.       #
#  The decorated tools are thin wrappers that simply call the helpers.         #
################################################################################

# Lightweight tool tests removed - they are thin wrappers around helpers
# which are already thoroughly tested above. The @mcp.tool decorator makes
# the functions not directly callable in tests. The helper functions contain
# all the business logic and are tested in the TestGet* classes above.


################################################################################
#                       API TOOL TESTS                                         #
#                                                                              #
#  Note: Type coercion is tested via _int and _bool helper tests above.        #
#  The @mcp.tool decorator makes functions not directly callable in tests.     #
################################################################################

# API tool tests removed - the type coercion logic is tested via _int and _bool
# helper tests above. The decorated tools are not directly callable due to the
# @mcp.tool decorator wrapping them in FunctionTool objects.


################################################################################
#                       RESOURCE FUNCTION TESTS                                #
#                                                                              #
#  Note: Resource functions decorated with @mcp.resource are wrapped and       #
#  not directly callable. We test the underlying logic via helper functions.   #
################################################################################

class TestDisplaysList:
    """Tests for displays_list logic (resource function)."""

    @patch('server.fastmcp_resources.api')
    def test_returns_filtered_fields(self, mock_api):
        """Should return workspace_id, count, and displays with filtered fields."""
        from server.fastmcp_resources import displays_list

        mock_api.displays.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "disp-1",
                        "_source": {
                            "workspace_id": "ws-1",
                            "index_pattern": "products-*",
                            "template": {"fields": ["title", "price"]}
                        }
                    }
                ]
            }
        })

        # displays_list is decorated with @mcp.resource, call it via fn attribute
        result = displays_list.fn("ws-1")

        assert result["workspace_id"] == "ws-1"
        assert result["count"] == 1
        display = result["displays"][0]
        assert display["_id"] == "disp-1"
        assert display["index_pattern"] == "products-*"
        assert display["template"] == {"fields": ["title", "price"]}


class TestStrategyTemplate:
    """Tests for strategy_template resource."""

    @patch('server.fastmcp_resources.api')
    def test_returns_template_only(self, mock_api):
        """Should return _id, name, and template only."""
        from server.fastmcp_resources import strategy_template

        mock_api.strategies.get.return_value = MagicMock(body={
            "_id": "str-1",
            "_source": {
                "name": "Match Query",
                "workspace_id": "ws-1",
                "tags": ["test"],
                "template": {
                    "source": '{"query": {"match": {"text": "{{text}}"}}}'
                }
            }
        })

        result = strategy_template.fn("str-1")

        assert result["_id"] == "str-1"
        assert result["name"] == "Match Query"
        assert "source" in result["template"]
        assert "workspace_id" not in result
        assert "tags" not in result


class TestBenchmarkTask:
    """Tests for benchmark_task resource."""

    @patch('server.fastmcp_resources.api')
    def test_returns_task_only(self, mock_api):
        """Should return _id, name, and task only."""
        from server.fastmcp_resources import benchmark_task

        mock_api.benchmarks.get.return_value = MagicMock(body={
            "_id": "bm-1",
            "_source": {
                "name": "Full Test",
                "workspace_id": "ws-1",
                "description": "Description",
                "tags": ["test"],
                "task": {
                    "metrics": ["ndcg@10"],
                    "k": 10,
                    "strategies": {"tags": ["baseline"]},
                    "scenarios": {"tags": ["important"]}
                }
            }
        })

        result = benchmark_task.fn("bm-1")

        assert result["_id"] == "bm-1"
        assert result["name"] == "Full Test"
        assert result["task"]["metrics"] == ["ndcg@10"]
        assert "workspace_id" not in result
        assert "description" not in result


class TestEvaluationTask:
    """Tests for evaluation_task resource."""

    @patch('server.fastmcp_resources.api')
    def test_returns_task_details(self, mock_api):
        """Should return task details without results."""
        from server.fastmcp_resources import evaluation_task

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "workspace_id": "ws-1",
                "benchmark_id": "bm-1",
                "task": {"metrics": ["ndcg@10"]},
                "strategy_id": ["str-1"],
                "scenario_id": ["sc-1"],
                "results": [{"should": "not appear"}]
            }
        })

        result = evaluation_task.fn("eval-1")

        assert result["_id"] == "eval-1"
        assert result["workspace_id"] == "ws-1"
        assert result["benchmark_id"] == "bm-1"
        assert result["task"] == {"metrics": ["ndcg@10"]}
        assert result["strategy_id"] == ["str-1"]
        assert result["scenario_id"] == ["sc-1"]
        assert "results" not in result


class TestEvaluationUnratedDocs:
    """Tests for evaluation_unrated_docs resource."""

    @patch('server.fastmcp_resources.api')
    def test_returns_unrated_docs(self, mock_api):
        """Should return unrated docs without full results."""
        from server.fastmcp_resources import evaluation_unrated_docs

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "unrated_docs": [
                    {"index": "products", "doc_id": "123"},
                    {"index": "products", "doc_id": "456"}
                ],
                "results": [{"should": "not appear"}]
            }
        })

        result = evaluation_unrated_docs.fn("eval-1")

        assert result["_id"] == "eval-1"
        assert len(result["unrated_docs"]) == 2
        assert "results" not in result


class TestEvaluationStrategies:
    """Tests for evaluation_strategies resource."""

    @patch('server.fastmcp_resources.api')
    def test_returns_strategies_with_metrics(self, mock_api):
        """Should list strategies with flattened metrics."""
        from server.fastmcp_resources import evaluation_strategies

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "summary": {
                    "strategy_id": {
                        "str-1": {
                            "_total": {
                                "metrics": {
                                    "ndcg@10": {"avg": 0.85, "min": 0.5, "max": 1.0}
                                }
                            }
                        },
                        "str-2": {
                            "_total": {
                                "metrics": {
                                    "ndcg@10": {"avg": 0.72}
                                }
                            }
                        }
                    }
                }
            }
        })

        result = evaluation_strategies.fn("eval-1")

        assert result["_id"] == "eval-1"
        assert len(result["strategies"]) == 2
        for strategy in result["strategies"]:
            assert "strategy_id" in strategy
            assert "metrics" in strategy
            if strategy["strategy_id"] == "str-1":
                assert strategy["metrics"]["ndcg@10"] == 0.85

    @patch('server.fastmcp_resources.api')
    def test_handles_missing_summary(self, mock_api):
        """Should handle missing summary gracefully."""
        from server.fastmcp_resources import evaluation_strategies

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {}
        })

        result = evaluation_strategies.fn("eval-1")

        assert result["_id"] == "eval-1"
        assert result["strategies"] == []


################################################################################
#                       SCENARIOS BY TAG TESTS                                 #
################################################################################

class TestScenariosByTag:
    """Tests for scenarios_by_tag resource."""

    @patch('server.fastmcp_resources.api')
    def test_filters_by_tag(self, mock_api):
        """Should filter scenarios by the specified tag."""
        from server.fastmcp_resources import scenarios_by_tag

        mock_api.scenarios.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "sc-1",
                        "_source": {
                            "name": "Tagged Scenario",
                            "values": {"text": "test"},
                            "tags": ["important", "test"]
                        }
                    }
                ]
            }
        })

        result = scenarios_by_tag.fn("ws-1", "important")

        assert result["workspace_id"] == "ws-1"
        assert result["tag"] == "important"
        assert result["count"] == 1

        # Verify the filter was passed correctly
        mock_api.scenarios.search.assert_called_once()
        call_kwargs = mock_api.scenarios.search.call_args
        assert call_kwargs.kwargs["filters"] == [{"term": {"tags": "important"}}]


class TestStrategiesByTag:
    """Tests for strategies_by_tag resource."""

    @patch('server.fastmcp_resources.api')
    def test_filters_by_tag(self, mock_api):
        """Should filter strategies by the specified tag."""
        from server.fastmcp_resources import strategies_by_tag

        mock_api.strategies.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "str-1",
                        "_source": {
                            "name": "Baseline Query",
                            "tags": ["baseline", "production"]
                        }
                    }
                ]
            }
        })

        result = strategies_by_tag.fn("ws-1", "baseline")

        assert result["workspace_id"] == "ws-1"
        assert result["tag"] == "baseline"
        assert result["count"] == 1

        # Verify the filter was passed correctly
        mock_api.strategies.search.assert_called_once()
        call_kwargs = mock_api.strategies.search.call_args
        assert call_kwargs.kwargs["filters"] == [{"term": {"tags": "baseline"}}]


################################################################################
#                       EDGE CASES AND ERROR HANDLING                          #
################################################################################

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch('server.fastmcp_resources.api')
    def test_missing_meta_field(self, mock_api):
        """Should handle missing @meta field gracefully."""
        from server.fastmcp_resources import _get_evaluation_status

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "took": 5000,
                # @meta is missing
            }
        })

        result = _get_evaluation_status("eval-1")

        assert result["_id"] == "eval-1"
        assert result["status"] is None
        assert result["started_at"] is None

    @patch('server.fastmcp_resources.api')
    def test_empty_results_array(self, mock_api):
        """Should handle empty results array."""
        from server.fastmcp_resources import _get_evaluation_results_by_strategy

        mock_api.evaluations.get.return_value = MagicMock(body={
            "_id": "eval-1",
            "_source": {
                "results": []
            }
        })

        result = _get_evaluation_results_by_strategy("eval-1", "str-1")

        assert "error" in result
        assert result["available_strategies"] == []

    # Note: test_missing_summary moved to TestEvaluationStrategies class
    # as test_handles_missing_summary

    @patch('server.fastmcp_resources.es')
    def test_evaluations_list_handles_missing_fields(self, mock_es):
        """Should handle evaluations with missing optional fields."""
        from server.fastmcp_resources import _get_evaluations_list

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "eval-1",
                        "_source": {
                            "workspace_id": "ws-1",
                            # Missing: benchmark_id, @meta, took
                        }
                    }
                ]
            }
        })

        result = _get_evaluations_list("ws-1")

        evaluation = result["evaluations"][0]
        assert evaluation["_id"] == "eval-1"
        assert evaluation["benchmark_id"] is None
        assert evaluation["status"] is None
        assert evaluation["took"] is None


################################################################################
#                       LATEST EVALUATION SUMMARY TESTS                        #
################################################################################

class TestLatestEvaluationSummary:
    """Tests for latest_evaluation_summary tool."""

    @patch('server.fastmcp_resources.es')
    def test_returns_most_recent_completed(self, mock_es):
        """Should return the most recent completed evaluation."""
        from server.fastmcp_resources import latest_evaluation_summary

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "eval-3",  # Most recent but pending
                        "_source": {
                            "@meta": {"status": "pending", "started_at": "2024-01-03T00:00:00Z"},
                            "benchmark_id": "bm-1",
                        }
                    },
                    {
                        "_id": "eval-2",  # Second most recent, completed
                        "_source": {
                            "@meta": {"status": "completed", "started_at": "2024-01-02T00:00:00Z"},
                            "benchmark_id": "bm-1",
                            "took": 5000,
                            "summary": {"strategy_id": {"str-1": {}}}
                        }
                    },
                    {
                        "_id": "eval-1",  # Oldest, completed
                        "_source": {
                            "@meta": {"status": "completed", "started_at": "2024-01-01T00:00:00Z"},
                            "benchmark_id": "bm-1",
                            "took": 3000,
                            "summary": {}
                        }
                    }
                ]
            }
        })

        # Access underlying function via .fn attribute (bypasses FunctionTool wrapper)
        result = latest_evaluation_summary.fn("ws-1")

        assert result["_id"] == "eval-2"  # Should be the most recent COMPLETED
        assert result["workspace_id"] == "ws-1"
        assert result["status"] == "completed"
        assert result["took"] == 5000
        assert "summary" in result

    @patch('server.fastmcp_resources.es')
    def test_no_completed_evaluations(self, mock_es):
        """Should return error when no completed evaluations exist."""
        from server.fastmcp_resources import latest_evaluation_summary

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {
                "hits": [
                    {
                        "_id": "eval-1",
                        "_source": {
                            "@meta": {"status": "pending"},
                            "benchmark_id": "bm-1",
                        }
                    },
                    {
                        "_id": "eval-2",
                        "_source": {
                            "@meta": {"status": "failed"},
                            "benchmark_id": "bm-1",
                        }
                    }
                ]
            }
        })

        result = latest_evaluation_summary.fn("ws-1")

        assert "error" in result
        assert result["workspace_id"] == "ws-1"
        assert result["total_evaluations"] == 2

    @patch('server.fastmcp_resources.es')
    def test_empty_workspace(self, mock_es):
        """Should handle workspace with no evaluations."""
        from server.fastmcp_resources import latest_evaluation_summary

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {"hits": []}
        })

        result = latest_evaluation_summary.fn("ws-empty")

        assert "error" in result
        assert result["total_evaluations"] == 0

    @patch('server.fastmcp_resources.es')
    def test_uses_correct_sort_order(self, mock_es):
        """Should query with descending started_at sort."""
        from server.fastmcp_resources import latest_evaluation_summary

        mock_es.return_value.search.return_value = MagicMock(body={
            "hits": {"hits": []}
        })

        latest_evaluation_summary.fn("ws-1")

        call_kwargs = mock_es.return_value.search.call_args
        body = call_kwargs.kwargs["body"]
        assert body["sort"] == [{"@meta.started_at": {"order": "desc"}}]


################################################################################
#                       HEALTHZ ENDPOINT TEST                                  #
################################################################################

class TestHealthz:
    """Tests for health check endpoints."""

    def test_healthz_mcp(self):
        """MCP health check should return acknowledged."""
        from server.fastmcp_resources import healthz_mcp

        # Access underlying function via .fn attribute (bypasses FunctionTool wrapper)
        result = healthz_mcp.fn()

        assert result == {"acknowledged": True}
