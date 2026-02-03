#!/usr/bin/env python3
"""
summarize_export.py のユニットテスト
"""

import sys
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from summarize_export import (
    extract_metric_values,
    calculate_percentiles,
    count_errors,
)


class TestExtractMetricValues:
    """extract_metric_values関数のテスト"""
    
    def test_extract_from_metrics_dict(self):
        """metrics辞書から値を抽出できることを確認"""
        data = [
            {"metrics": {"time_to_first_token": 123.45}},
            {"metrics": {"time_to_first_token": 234.56}},
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 2
        assert values[0] == 123.45
        assert values[1] == 234.56
    
    def test_extract_from_dict_value(self):
        """辞書形式の値（{'value': ..., 'unit': 'ms'}）から抽出できることを確認"""
        data = [
            {"metrics": {"time_to_first_token": {"value": 123.45, "unit": "ms"}}},
            {"metrics": {"time_to_first_token": {"value": 234.56, "unit": "ms"}}},
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 2
        assert values[0] == 123.45
        assert values[1] == 234.56
    
    def test_extract_with_alternative_names(self):
        """別名（ttft）からも抽出できることを確認"""
        data = [
            {"metrics": {"ttft": 123.45}},
            {"metrics": {"time_to_first_token_ms": 234.56}},
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 2
        assert values[0] == 123.45
        assert values[1] == 234.56
    
    def test_unit_conversion_from_seconds(self):
        """秒→ミリ秒の変換が正しく行われることを確認"""
        data = [
            {"metrics": {"time_to_first_token": 0.5}},  # 0.5秒 = 500ms
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 1
        assert values[0] == 500.0
    
    def test_unit_conversion_from_nanoseconds(self):
        """ナノ秒→ミリ秒の変換が正しく行われることを確認"""
        data = [
            {"metrics": {"time_to_first_token": 2_000_000_000}},  # 2秒 = 2,000ms
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 1
        # ナノ秒単位（> 1,000,000,000）の場合、1,000,000で割る
        assert values[0] == 2000.0
    
    def test_no_conversion_for_milliseconds(self):
        """ミリ秒の値はそのまま使用されることを確認"""
        data = [
            {"metrics": {"time_to_first_token": 123.45}},  # 既にms単位
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 1
        assert values[0] == 123.45
    
    def test_skip_invalid_values(self):
        """無効な値（辞書だがvalueキーがない）はスキップされることを確認"""
        data = [
            {"metrics": {"time_to_first_token": 123.45}},
            {"metrics": {"time_to_first_token": {"unit": "ms"}}},  # valueキーがない
            {"metrics": {"time_to_first_token": 234.56}},
        ]
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 2
        assert values[0] == 123.45
        assert values[1] == 234.56
    
    def test_empty_data(self):
        """空のデータの場合、空のリストが返されることを確認"""
        data = []
        values = extract_metric_values(data, "time_to_first_token")
        assert len(values) == 0


class TestCalculatePercentiles:
    """calculate_percentiles関数のテスト"""
    
    def test_calculate_percentiles_basic(self):
        """基本的なパーセンタイル計算が正しく行われることを確認"""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        stats = calculate_percentiles(values)
        
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert "avg" in stats
        
        assert stats["p50"] == 5.5  # 中央値
        assert stats["avg"] == 5.5  # 平均
    
    def test_calculate_percentiles_empty(self):
        """空のリストの場合、すべて0が返されることを確認"""
        values = []
        stats = calculate_percentiles(values)
        
        assert stats["p50"] == 0.0
        assert stats["p95"] == 0.0
        assert stats["p99"] == 0.0
        assert stats["avg"] == 0.0
    
    def test_calculate_percentiles_single_value(self):
        """単一の値の場合、すべてその値が返されることを確認"""
        values = [100.0]
        stats = calculate_percentiles(values)
        
        assert stats["p50"] == 100.0
        assert stats["p95"] == 100.0
        assert stats["p99"] == 100.0
        assert stats["avg"] == 100.0
    
    def test_calculate_percentiles_with_real_data(self):
        """実際のベンチマークデータに近い値でテスト"""
        values = [490.19, 500.0, 550.0, 600.0, 650.0, 700.0, 750.0, 790.01, 850.0, 991.75]
        stats = calculate_percentiles(values)
        
        assert 650 <= stats["p50"] <= 700  # p50は中央値（5番目と6番目の平均）
        assert stats["p95"] > 790  # p95は高い値
        assert stats["p99"] > 850  # p99はさらに高い値
        assert 650 < stats["avg"] < 700  # 平均は中央付近


class TestCountErrors:
    """count_errors関数のテスト"""
    
    def test_count_errors_with_error_field(self):
        """errorフィールドを持つレコードをカウントできることを確認"""
        data = [
            {"error": "Some error"},
            {"error": None},
            {"error": "Another error"},
        ]
        error_count = count_errors(data)
        assert error_count == 2
    
    def test_count_errors_with_status_field(self):
        """statusフィールドを持つレコードをカウントできることを確認"""
        data = [
            {"status": "success"},
            {"status": "error"},
            {"status": "failed"},
        ]
        error_count = count_errors(data)
        assert error_count == 2
    
    def test_count_errors_with_success_field(self):
        """successフィールドを持つレコードをカウントできることを確認"""
        data = [
            {"success": True},
            {"success": False},
            {"success": False},
        ]
        error_count = count_errors(data)
        assert error_count == 2
    
    def test_count_errors_no_errors(self):
        """エラーがない場合、0が返されることを確認"""
        data = [
            {"status": "success"},
            {"success": True},
        ]
        error_count = count_errors(data)
        assert error_count == 0
    
    def test_count_errors_empty_data(self):
        """空のデータの場合、0が返されることを確認"""
        data = []
        error_count = count_errors(data)
        assert error_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
