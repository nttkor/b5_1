"""해시맵 리사이징 및 대규모 데이터 처리 성능 벤치마크 도구.

본 스크립트는 Mini Redis의 HashMap 및 MiniRedisStore 엔진을 대상으로
대규모 키-값 쌍(10,000 ~ 100,000건) 삽입 및 조회 시의 리사이징/리해싱 소요 시간,
체인 길이 분포, 처리율(ops/sec)을 정밀 측정하여 병목 분석 데이터를 제공합니다.
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 src 모듈 임포트 가능하도록 설정
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.hashmap import HashMap
from src.store import MiniRedisStore


def benchmark_hashmap(n_items=10000):
    """지정된 개수의 항목을 HashMap에 삽입 및 조회하며 성능 지표를 측정합니다.

    Args:
        n_items (int): 삽입할 총 키-값 쌍 개수 (기본값: 10,000).

    Returns:
        dict: 삽입 시간, 조회 시간, 리해시 횟수, 최종 용량, 최대 체인 길이 등 측정 결과 딕셔너리.
    """
    hm = HashMap(capacity=8)

    # 1. 삽입 및 리해시 벤치마크
    start_put = time.perf_counter()
    for i in range(n_items):
        hm.put(f"bench_key_{i}", f"value_{i}")
    end_put = time.perf_counter()
    put_duration = end_put - start_put
    put_ops = n_items / put_duration if put_duration > 0 else 0

    # 2. 조회(GET) 벤치마크
    start_get = time.perf_counter()
    for i in range(n_items):
        _ = hm.get(f"bench_key_{i}")
    end_get = time.perf_counter()
    get_duration = end_get - start_get
    get_ops = n_items / get_duration if get_duration > 0 else 0

    # 3. 체인 통계 수집
    cap, size, empty_cnt, max_chain, avg_chain = hm.get_chain_stats()
    rehash_count = len(hm.rehash_history)

    return {
        "n_items": n_items,
        "put_time_sec": put_duration,
        "put_ops_sec": put_ops,
        "get_time_sec": get_duration,
        "get_ops_sec": get_ops,
        "final_capacity": cap,
        "rehash_count": rehash_count,
        "empty_buckets": empty_cnt,
        "max_chain": max_chain,
        "avg_chain": avg_chain,
    }


def run_full_benchmark():
    """10k, 50k, 100k 건에 대한 단계별 벤치마크를 수행하고 종합 결과를 출력합니다."""
    print("=" * 72)
    print("🚀 Mini Redis HashMap & Resizing Performance Benchmark")
    print("=" * 72)
    
    test_sizes = [10000, 50000, 100000]
    results = []

    for size in test_sizes:
        print(f"[*] Benchmarking {size:,} items...", flush=True)
        res = benchmark_hashmap(size)
        results.append(res)

    print("\n" + "=" * 72)
    print("📊 벤치마크 측정 결과 요약표 (Benchmark Summary)")
    print("=" * 72)
    header = f"{'항목수 (Items)':<14} | {'삽입 시간(s)':<12} | {'삽입 ops/s':<12} | {'조회 ops/s':<12} | {'최종버킷수':<10} | {'최대체인':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        line = (
            f"{r['n_items']:<14,d} | "
            f"{r['put_time_sec']:<12.4f} | "
            f"{r['put_ops_sec']:<12.0f} | "
            f"{r['get_ops_sec']:<12.0f} | "
            f"{r['final_capacity']:<10,d} | "
            f"{r['max_chain']:<8d}"
        )
        print(line)
    print("=" * 72)

    print("\n📋 마크다운 테이블 복사용:")
    print("| 데이터 규모 | 삽입 소요 시간 (s) | 삽입 Throughput | 조회 Throughput | 최종 버킷 수 | 리해시 횟수 | 최대 체인 길이 | 평균 체인 길이 |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for r in results:
        print(
            f"| **{r['n_items']:,}건** | {r['put_time_sec']:.4f}s | "
            f"{r['put_ops_sec']:,.0f} ops/s | {r['get_ops_sec']:,.0f} ops/s | "
            f"{r['final_capacity']:,} | {r['rehash_count']}회 | "
            f"{r['max_chain']} | {r['avg_chain']:.2f} |"
        )
    return results


if __name__ == "__main__":
    run_full_benchmark()
