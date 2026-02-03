#!/usr/bin/env python3
"""
AIPerfのexport結果からp50/p95/p99を算出してTSVサマリを生成
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import statistics

def find_latest_artifact_dir() -> Optional[Path]:
    """最新のartifactディレクトリを探す"""
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        print("Error: artifacts/ directory not found", file=sys.stderr)
        return None
    
    # サブディレクトリを取得して最新のものを選択
    subdirs = [d for d in artifacts_dir.iterdir() if d.is_dir()]
    if not subdirs:
        print("Error: No artifact subdirectories found", file=sys.stderr)
        return None
    
    # 更新時刻でソート（最新が先頭）
    subdirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return subdirs[0]

def find_export_files(artifact_dir: Path) -> List[Path]:
    """exportファイルを探す（profile_export.jsonl または profile_export*.json）"""
    export_files = []
    
    # profile_export.jsonl を探す
    jsonl_file = artifact_dir / "profile_export.jsonl"
    if jsonl_file.exists():
        export_files.append(jsonl_file)
    
    # profile_export*.json を探す
    for json_file in artifact_dir.glob("profile_export*.json"):
        export_files.append(json_file)
    
    return export_files

def load_export_data(export_files: List[Path]) -> List[Dict]:
    """exportファイルからデータを読み込む"""
    all_data = []
    
    for export_file in export_files:
        print(f"Loading: {export_file}", file=sys.stderr)
        
        if export_file.suffix == ".jsonl":
            # JSONL形式（1行1JSON）
            with open(export_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            all_data.append(data)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Failed to parse line in {export_file}: {e}", file=sys.stderr)
        else:
            # JSON形式
            with open(export_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    # 配列の場合は展開
                    if isinstance(data, list):
                        all_data.extend(data)
                    else:
                        all_data.append(data)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse {export_file}: {e}", file=sys.stderr)
    
    return all_data

def extract_metric_values(data: List[Dict], metric_name: str) -> List[float]:
    """指定されたメトリクスの値を抽出（ms単位に変換）"""
    values = []
    
    for record in data:
        # 様々な可能性のあるフィールド名を試す
        value = None
        
        # AIPerfのexport形式: metrics.time_to_first_token など
        if "metrics" in record and isinstance(record["metrics"], dict):
            metrics = record["metrics"]
            if metric_name in metrics:
                value = metrics[metric_name]
        
        # 直接フィールド
        if value is None and metric_name in record:
            value = record[metric_name]
        
        # 別名（例: ttft, latency）
        if value is None and metric_name == "time_to_first_token":
            for alt_name in ["ttft", "time_to_first_token_ms", "first_token_latency", "time_to_first_output_token"]:
                if "metrics" in record and isinstance(record["metrics"], dict) and alt_name in record["metrics"]:
                    value = record["metrics"][alt_name]
                    break
                elif alt_name in record:
                    value = record[alt_name]
                    break
        elif value is None and metric_name == "request_latency":
            for alt_name in ["latency", "request_latency_ms", "end_to_end_latency", "e2e_latency"]:
                if "metrics" in record and isinstance(record["metrics"], dict) and alt_name in record["metrics"]:
                    value = record["metrics"][alt_name]
                    break
                elif alt_name in record:
                    value = record[alt_name]
                    break
        elif value is None and metric_name == "inter_token_latency":
            for alt_name in ["itl", "inter_token_latency_ms", "token_latency", "inter_chunk_latency"]:
                if "metrics" in record and isinstance(record["metrics"], dict) and alt_name in record["metrics"]:
                    value = record["metrics"][alt_name]
                    break
                elif alt_name in record:
                    value = record[alt_name]
                    break
        
        if value is not None:
            # AIPerfのexport形式: {'value': 458.1325, 'unit': 'ms'} のような辞書形式
            if isinstance(value, dict):
                if "value" in value:
                    value = value["value"]
                else:
                    continue  # 辞書形式だがvalueキーがない場合はスキップ
            
            # 値の単位を変換（AIPerfのexportは既にms単位で出力される）
            if isinstance(value, (int, float)):
                # AIPerfのexportは通常ms単位なので、そのまま使用
                # ただし、異常に大きい値（ナノ秒）や小さい値（秒）の場合は変換
                # ナノ秒単位の可能性をチェック（非常に大きい値、例: 1秒 = 1,000,000,000ns）
                if value > 1_000_000_000:
                    value = value / 1_000_000  # ナノ秒→ms
                # 秒単位の可能性（1未満の値、例: 0.5秒）
                elif value < 1:
                    value = value * 1000  # 秒→ms
                # それ以外はms単位と仮定（1以上1,000,000,000未満）
                values.append(float(value))
    
    return values

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """パーセンタイルを計算"""
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    def percentile(p: float) -> float:
        if n == 0:
            return 0.0
        k = (n - 1) * p
        f = int(k)
        c = k - f
        if f + 1 < n:
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        return sorted_values[f]
    
    return {
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "avg": statistics.mean(sorted_values) if sorted_values else 0.0,
    }

def count_errors(data: List[Dict]) -> int:
    """エラー数をカウント"""
    error_count = 0
    for record in data:
        # 様々なエラー判定方法
        if "error" in record and record["error"]:
            error_count += 1
        elif "status" in record and record["status"] != "success":
            error_count += 1
        elif "success" in record and not record["success"]:
            error_count += 1
    return error_count

def main():
    # 最新のartifactディレクトリを探す
    artifact_dir = find_latest_artifact_dir()
    if not artifact_dir:
        sys.exit(1)
    
    print(f"Using artifact directory: {artifact_dir}", file=sys.stderr)
    
    # exportファイルを探す
    export_files = find_export_files(artifact_dir)
    if not export_files:
        print(f"Error: No export files found in {artifact_dir}", file=sys.stderr)
        sys.exit(1)
    
    # データを読み込む
    data = load_export_data(export_files)
    if not data:
        print("Error: No data found in export files", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loaded {len(data)} records", file=sys.stderr)
    
    # メトリクス定義
    metrics = [
        ("time_to_first_token", "TTFT"),
        ("request_latency", "Request Latency"),
        ("inter_token_latency", "Inter-Token Latency"),
    ]
    
    # TSV出力
    tsv_lines = ["metric\tp50_ms\tp95_ms\tp99_ms\tavg_ms\tcount\terrors"]
    
    # 各メトリクスを処理
    for metric_name, display_name in metrics:
        values = extract_metric_values(data, metric_name)
        
        if not values:
            print(f"Warning: No values found for {metric_name}", file=sys.stderr)
            continue
        
        stats = calculate_percentiles(values)
        error_count = count_errors(data)
        
        tsv_lines.append(
            f"{display_name}\t"
            f"{stats['p50']:.2f}\t"
            f"{stats['p95']:.2f}\t"
            f"{stats['p99']:.2f}\t"
            f"{stats['avg']:.2f}\t"
            f"{len(values)}\t"
            f"{error_count}"
        )
    
    # TSVファイルに書き出し
    tsv_content = "\n".join(tsv_lines)
    with open("summary.tsv", "w", encoding="utf-8") as f:
        f.write(tsv_content)
    
    print("\n" + "=" * 60, file=sys.stderr)
    print("Summary (TSV):", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(tsv_content)
    print("=" * 60, file=sys.stderr)
    print(f"\nSummary saved to: summary.tsv", file=sys.stderr)
    
    # Markdown形式のサマリも生成（任意）
    md_lines = [
        "# Benchmark Summary",
        "",
        f"**Artifact Directory:** `{artifact_dir}`",
        f"**Total Records:** {len(data)}",
        "",
        "## Metrics",
        "",
        "| Metric | p50 (ms) | p95 (ms) | p99 (ms) | Avg (ms) | Count | Errors |",
        "|--------|----------|----------|----------|----------|-------|--------|",
    ]
    
    for metric_name, display_name in metrics:
        values = extract_metric_values(data, metric_name)
        if values:
            stats = calculate_percentiles(values)
            error_count = count_errors(data)
            md_lines.append(
                f"| {display_name} | {stats['p50']:.2f} | {stats['p95']:.2f} | "
                f"{stats['p99']:.2f} | {stats['avg']:.2f} | {len(values)} | {error_count} |"
            )
    
    md_content = "\n".join(md_lines)
    with open("summary.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"Markdown summary saved to: summary.md", file=sys.stderr)

if __name__ == "__main__":
    main()
