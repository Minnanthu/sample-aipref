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


def extract_tokens_per_sec(data: List[Dict]) -> List[float]:
    """各リクエストの output tokens/sec を計算"""
    values = []

    for record in data:
        token_count = None
        latency_ms = None

        # token_count を探す（フィールド名の候補リスト）
        token_fields = [
            "token_count", "output_token_count", "output_tokens",
            "completion_tokens", "generated_tokens", "output_sequence_length"
        ]
        for field in token_fields:
            # 直接フィールド
            if field in record and record[field] is not None:
                token_count = record[field]
                break
            # metrics 辞書内
            if "metrics" in record and isinstance(record["metrics"], dict):
                if field in record["metrics"] and record["metrics"][field] is not None:
                    token_count = record["metrics"][field]
                    break

        # request_latency_ms を探す（フィールド名の候補リスト）
        latency_fields = [
            "request_latency_ms", "request_latency", "latency", "e2e_latency"
        ]
        for field in latency_fields:
            # 直接フィールド
            if field in record and record[field] is not None:
                latency_ms = record[field]
                break
            # metrics 辞書内
            if "metrics" in record and isinstance(record["metrics"], dict):
                if field in record["metrics"] and record["metrics"][field] is not None:
                    latency_ms = record["metrics"][field]
                    break

        # 両方の値が取得できた場合のみ計算
        if token_count is not None and latency_ms is not None:
            # 辞書形式の場合は value を取得
            if isinstance(token_count, dict) and "value" in token_count:
                token_count = token_count["value"]
            if isinstance(latency_ms, dict) and "value" in latency_ms:
                latency_ms = latency_ms["value"]

            if isinstance(token_count, (int, float)) and isinstance(latency_ms, (int, float)):
                if latency_ms > 0:
                    # latency_ms を秒に変換して tokens/sec を計算
                    latency_sec = latency_ms / 1000.0
                    tokens_per_sec = token_count / latency_sec
                    values.append(tokens_per_sec)

    return values

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
    
    # メトリクス定義（latency系、単位: ms）
    latency_metrics = [
        ("time_to_first_token", "TTFT"),
        ("request_latency", "Request Latency"),
        ("inter_token_latency", "Inter-Token Latency"),
    ]

    # TSV出力
    tsv_lines = ["metric\tp50\tp95\tp99\tavg\tunit\tcount\terrors"]
    error_count = count_errors(data)

    # Latency系メトリクスを処理
    for metric_name, display_name in latency_metrics:
        values = extract_metric_values(data, metric_name)

        if not values:
            print(f"Warning: No values found for {metric_name}", file=sys.stderr)
            continue

        stats = calculate_percentiles(values)

        tsv_lines.append(
            f"{display_name}\t"
            f"{stats['p50']:.2f}\t"
            f"{stats['p95']:.2f}\t"
            f"{stats['p99']:.2f}\t"
            f"{stats['avg']:.2f}\t"
            f"ms\t"
            f"{len(values)}\t"
            f"{error_count}"
        )

    # Throughput: Output Tokens/sec を処理（avg のみ、p50/p95/p99 は N/A）
    # 注: tokens/sec はシステム全体のスループットを表すため、パーセンタイルは意味をなさない
    tps_values = extract_tokens_per_sec(data)
    if tps_values:
        tps_avg = statistics.mean(tps_values)
        tsv_lines.append(
            f"Output Tokens/sec\t"
            f"N/A\t"
            f"N/A\t"
            f"N/A\t"
            f"{tps_avg:.2f}\t"
            f"tokens/s\t"
            f"{len(tps_values)}\t"
            f"{error_count}"
        )
    else:
        print("Warning: No values found for tokens/sec (missing token_count or request_latency)", file=sys.stderr)
    
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
        "| Metric | p50 | p95 | p99 | Avg | Unit | Count | Errors |",
        "|--------|-----|-----|-----|-----|------|-------|--------|",
    ]

    # Latency系メトリクス
    for metric_name, display_name in latency_metrics:
        values = extract_metric_values(data, metric_name)
        if values:
            stats = calculate_percentiles(values)
            md_lines.append(
                f"| {display_name} | {stats['p50']:.2f} | {stats['p95']:.2f} | "
                f"{stats['p99']:.2f} | {stats['avg']:.2f} | ms | {len(values)} | {error_count} |"
            )

    # Throughput: Output Tokens/sec（avg のみ）
    if tps_values:
        md_lines.append(
            f"| Output Tokens/sec | N/A | N/A | "
            f"N/A | {tps_avg:.2f} | tokens/s | {len(tps_values)} | {error_count} |"
        )

    md_content = "\n".join(md_lines)
    with open("summary.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Markdown summary saved to: summary.md", file=sys.stderr)

if __name__ == "__main__":
    main()
