#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5G Hierarchical MEC Host Selection Simulation (Local Edge vs. Regional Edge)
Aligned with Simu5G Architecture (TopoT2: gNB -> I-UPF -> Anchor UPF -> MEC Hosts)

Author: Mai Cuong Tho (thomc@ntu.edu.vn)
Description:
    Simulates real-time task offloading and hierarchical MEC host selection in a 5G
    network featuring two local edge hosts (mecHost1, mecHost2 attached to iUpf1, iUpf2)
    and one high-capacity regional edge host (mecHost3 attached to Anchor UPF).
    Evaluates Load & Latency Aware policy against Local Edge Only and Round Robin,
    incorporating X2 handover, burst traffic, and UE local fallback mechanisms.
"""

import copy
import random
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
# 1. SYSTEM CONFIGURATION & HIERARCHICAL 5G MEC TOPOLOGY
# ==============================================================================
RANDOM_SEED = 42
NUM_TASKS = 120
ALPHA_WEIGHT = 0.55   # Weight for normalized end-to-end latency
BETA_WEIGHT = 0.45    # Weight for projected CPU load ratio
LATENCY_REF_MS = 100.0  # Normalization reference (100 ms)

# 5G NR Radio Uplink Rates (Mbps) per UE
UE_PROFILES = [
    {"id": "ue[0]", "type": "5G Smartphone", "gnb": "gnb1", "ul_rate_mbps": 120.0, "local_cpu": 1500.0},
    {"id": "ue[1]", "type": "V2X Vehicle",   "gnb": "gnb1", "ul_rate_mbps": 95.0,  "local_cpu": 2000.0},
    {"id": "ue[2]", "type": "5G Camera",     "gnb": "gnb2", "ul_rate_mbps": 140.0, "local_cpu": 1200.0},
]

# Hierarchical MEC Hosts (aligned with Simu5G TopoT2.ned)
BASE_MEC_HOSTS = [
    {
        "name": "mecHost1",
        "tier": "Local Edge (iUpf1)",
        "attached_gnb": "gnb1",
        "cpu_mips": 10000.0,       # 10,000 MIPS
        "link_delay_ms": 1.0,      # mecHost1LinkDelay = 1ms
        "max_queue_mc": 8000.0,    # Admission control threshold
        "queue_mc": 0.0,
    },
    {
        "name": "mecHost2",
        "tier": "Local Edge (iUpf2)",
        "attached_gnb": "gnb2",
        "cpu_mips": 10000.0,       # 10,000 MIPS
        "link_delay_ms": 1.0,      # mecHost2LinkDelay = 1ms
        "max_queue_mc": 8000.0,
        "queue_mc": 0.0,
    },
    {
        "name": "mecHost3",
        "tier": "Regional Edge (Anchor UPF)",
        "attached_gnb": "anchor",
        "cpu_mips": 32000.0,       # 32,000 MIPS (High-capacity central edge)
        "link_delay_ms": 18.0,     # mecHost3LinkDelay = 18ms
        "max_queue_mc": 24000.0,
        "queue_mc": 0.0,
    },
]

# Backhaul / N9 interface latency matrix (ms) from serving gNB to target MEC Host
BACKHAUL_MATRIX_MS = {
    ("gnb1", "mecHost1"): 0.5,   # Direct local breakout at iUpf1
    ("gnb1", "mecHost2"): 6.0,   # Cross-site via iUpf1 -> Anchor UPF -> iUpf2
    ("gnb1", "mecHost3"): 2.0,   # Upstream via iUpf1 -> Anchor UPF
    ("gnb2", "mecHost1"): 6.0,   # Cross-site via iUpf2 -> Anchor UPF -> iUpf1
    ("gnb2", "mecHost2"): 0.5,   # Direct local breakout at iUpf2
    ("gnb2", "mecHost3"): 2.0,   # Upstream via iUpf2 -> Anchor UPF
}


# ==============================================================================
# 2. WORKLOAD GENERATOR (WITH BURST TRAFFIC & X2 HANDOVER EVENTS)
# ==============================================================================
def generate_5g_workload(num_tasks: int, seed: int = RANDOM_SEED):
    """Generates a deterministic sequence of 5G MEC tasks with burst & handover events."""
    rng = random.Random(seed)
    ues = copy.deepcopy(UE_PROFILES)
    workload = []
    current_time_s = 0.0

    for idx in range(1, num_tasks + 1):
        # Simulate X2 Handover for V2X Vehicle (ue[1]) from gnb1 to gnb2 at task 45
        handover_event = False
        if idx == 45:
            ues[1]["gnb"] = "gnb2"
            handover_event = True

        # Simulate Burst Traffic window between task 65 and 90
        is_burst = (65 <= idx <= 90)
        inter_arrival_s = rng.uniform(0.03, 0.08) if is_burst else rng.uniform(0.12, 0.35)
        current_time_s += inter_arrival_s

        ue = copy.deepcopy(rng.choice(ues))
        data_size_mb = rng.uniform(1.5, 5.0) if is_burst else rng.uniform(0.5, 2.5)
        comp_cycles_mc = rng.uniform(900.0, 2200.0) if is_burst else rng.uniform(400.0, 1200.0)

        workload.append({
            "task_id": idx,
            "timestamp_s": current_time_s,
            "delta_t_s": inter_arrival_s,
            "ue": ue,
            "data_mb": data_size_mb,
            "cycles_mc": comp_cycles_mc,
            "is_burst": is_burst,
            "handover": handover_event,
        })

    return workload


# ==============================================================================
# 3. LATENCY & LOAD MODELS + MEC ORCHESTRATOR SELECTION POLICIES
# ==============================================================================
def estimate_e2e_latency_ms(ue: dict, host: dict, data_mb: float, cycles_mc: float) -> float:
    """
    Computes 4-component 5G MEC End-to-End Latency (in ms):
      1. 5G NR Uplink/Downlink Radio Delay
      2. Backhaul (N3/N9) + MEC Access Link Delay
      3. Queue Waiting Delay at target MEC Host
      4. CPU Execution Delay at target MEC Host
    """
    # 1. Radio transmission delay (assuming downlink result is ~10% of uplink data)
    radio_delay_ms = ((data_mb * 1.1 * 8.0) / ue["ul_rate_mbps"]) * 1000.0

    # 2. Transport + Access link delay
    bh_delay_ms = BACKHAUL_MATRIX_MS[(ue["gnb"], host["name"])] + host["link_delay_ms"]

    # 3. Queue waiting time (s -> ms)
    wait_delay_ms = (host["queue_mc"] / host["cpu_mips"]) * 1000.0

    # 4. Execution time (s -> ms)
    exec_delay_ms = (cycles_mc / host["cpu_mips"]) * 1000.0

    return radio_delay_ms + bh_delay_ms + wait_delay_ms + exec_delay_ms


def select_mec_host(strategy: str, task: dict, hosts: list, rr_counter: int):
    """Selects optimal MEC Host based on the active orchestration policy."""
    ue = task["ue"]
    cycles = task["cycles_mc"]
    data_mb = task["data_mb"]

    # Filter hosts passing Admission Control (queue + new task <= max_queue)
    admissible = [h for h in hosts if (h["queue_mc"] + cycles) <= h["max_queue_mc"]]
    if not admissible:
        return None  # Triggers UE Local Fallback

    if strategy == "Round_Robin":
        # Cycles across admissible hosts
        return admissible[rr_counter % len(admissible)]

    if strategy == "Local_Edge_Only":
        # Strictly prefers local edge host co-located with serving gNB
        local_name = "mecHost1" if ue["gnb"] == "gnb1" else "mecHost2"
        for h in admissible:
            if h["name"] == local_name:
                return h
        # If local host is saturated, fall back to UE local execution
        return None

    if strategy == "Load_Latency_Aware":
        best_host = None
        min_score = float("inf")

        for h in admissible:
            e2e_ms = estimate_e2e_latency_ms(ue, h, data_mb, cycles)
            projected_load = (h["queue_mc"] + cycles) / h["max_queue_mc"]
            norm_latency = e2e_ms / LATENCY_REF_MS

            score = (ALPHA_WEIGHT * norm_latency) + (BETA_WEIGHT * projected_load)
            if score < min_score:
                min_score = score
                best_host = h

        return best_host

    raise ValueError(f"Unknown policy strategy: {strategy}")


# ==============================================================================
# 4. REAL-TIME SIMULATION ENGINE
# ==============================================================================
def run_policy_simulation(strategy: str, workload: list):
    """Executes the discrete-event simulation for a given selection policy."""
    hosts = copy.deepcopy(BASE_MEC_HOSTS)
    latencies_ms = []
    cluster_cpu_pct = []
    host_load_traces = {h["name"]: [] for h in hosts}
    host_task_counts = {h["name"]: 0 for h in hosts}
    fallback_count = 0
    rr_counter = 0

    for task in workload:
        dt = task["delta_t_s"]

        # Release processed CPU cycles over elapsed time dt
        for h in hosts:
            processed_mc = h["cpu_mips"] * dt
            h["queue_mc"] = max(0.0, h["queue_mc"] - processed_mc)

        # Select MEC Host via Orchestrator policy
        chosen = select_mec_host(strategy, task, hosts, rr_counter)
        rr_counter += 1

        if chosen is None:
            # UE Local Execution Fallback when MEC hosts are saturated or restricted
            fallback_count += 1
            e2e_ms = (task["cycles_mc"] / task["ue"]["local_cpu"]) * 1000.0
        else:
            e2e_ms = estimate_e2e_latency_ms(task["ue"], chosen, task["data_mb"], task["cycles_mc"])
            chosen["queue_mc"] += task["cycles_mc"]
            host_task_counts[chosen["name"]] += 1

        latencies_ms.append(e2e_ms)

        # Record utilization metrics
        total_q = sum(h["queue_mc"] for h in hosts)
        total_cap = sum(h["max_queue_mc"] for h in hosts)
        cluster_cpu_pct.append((total_q / total_cap) * 100.0)

        for h in hosts:
            host_load_traces[h["name"]].append((h["queue_mc"] / h["max_queue_mc"]) * 100.0)

    mean_host_loads = [np.mean(host_load_traces[h["name"]]) for h in hosts]
    return {
        "strategy": strategy,
        "latencies_ms": latencies_ms,
        "avg_latency_ms": float(np.mean(latencies_ms)),
        "p95_latency_ms": float(np.percentile(latencies_ms, 95)),
        "cluster_cpu_pct": cluster_cpu_pct,
        "mean_host_loads": mean_host_loads,
        "load_std": float(np.std(mean_host_loads)),
        "task_counts": host_task_counts,
        "fallback_count": fallback_count,
    }


# ==============================================================================
# 5. REPORTING & VISUALIZATION
# ==============================================================================
def print_summary_table(results: list):
    print("=" * 92)
    print("5G HIERARCHICAL MEC HOST SELECTION - SIMULATION BENCHMARK SUMMARY")
    print("Author: Mai Cuong Tho (thomc@ntu.edu.vn) | Topology: Simu5G TopoT2 (3 MEC Hosts)")
    print("=" * 92)
    header = f"{'Policy Strategy':<22} | {'Avg Lat (ms)':>12} | {'P95 Lat (ms)':>12} | {'Load Std (%)':>12} | {'UE Fallback':>11} | {'Tasks (H1/H2/H3)'}"
    print(header)
    print("-" * 92)
    for r in results:
        tc = r["task_counts"]
        dist = f"{tc['mecHost1']}/{tc['mecHost2']}/{tc['mecHost3']}"
        print(
            f"{r['strategy']:<22} | "
            f"{r['avg_latency_ms']:>12.2f} | "
            f"{r['p95_latency_ms']:>12.2f} | "
            f"{r['load_std']:>12.2f} | "
            f"{r['fallback_count']:>11d} | "
            f"{dist}"
        )
    print("=" * 92)


def plot_benchmark_charts(workload: list, results: list, output_file: str = "5g_mec_topot2_benchmark.png"):
    timestamps = [t["timestamp_s"] for t in workload]
    res_local, res_rr, res_smart = results

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle(
        "5G Hierarchical MEC Host Selection Benchmark (Local Edge vs. Regional Edge)",
        fontsize=14,
        fontweight="bold",
    )

    # Subplot 1: Real-time End-to-End Latency
    ax1.plot(timestamps, res_local["latencies_ms"], label="Local Edge Only", color="#ef4444", alpha=0.65, linestyle="--")
    ax1.plot(timestamps, res_rr["latencies_ms"], label="Round Robin", color="#f59e0b", alpha=0.8, linestyle="-.")
    ax1.plot(timestamps, res_smart["latencies_ms"], label="Load & Latency Aware", color="#0284c7", linewidth=2.2)
    ax1.axvspan(timestamps[64], timestamps[89], color="#fde047", alpha=0.22, label="Burst Traffic Window")
    ax1.set_title("1. Real-Time End-to-End Task Latency", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Simulation Time (s)")
    ax1.set_ylabel("End-to-End Latency (ms)")
    ax1.legend(fontsize=8.5)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Subplot 2: Average & P95 Latency Comparison
    labels = ["Local Edge
Only", "Round
Robin", "Load & Latency
Aware"]
    avg_vals = [r["avg_latency_ms"] for r in results]
    p95_vals = [r["p95_latency_ms"] for r in results]
    x = np.arange(len(labels))
    w = 0.35

    b1 = ax2.bar(x - w / 2, avg_vals, w, label="Mean Latency (ms)", color=["#ef4444", "#f59e0b", "#0284c7"])
    b2 = ax2.bar(x + w / 2, p95_vals, w, label="95th Percentile (ms)", color=["#fca5a5", "#fcd34d", "#7dd3fc"])
    ax2.set_title("2. Mean vs. P95 Latency Comparison", fontsize=11, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Latency (ms)")
    ax2.set_ylim(0, max(p95_vals) * 1.22)
    ax2.legend(fontsize=8.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in b1:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 3, f"{h:.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # Subplot 3: Hierarchical Load Balancing Across 3 MEC Hosts
    host_labels = ["mecHost1
(iUpf1 - 10k)", "mecHost2
(iUpf2 - 10k)", "mecHost3
(Anchor - 32k)"]
    xh = np.arange(len(host_labels))
    wh = 0.25

    ax3.bar(xh - wh, res_local["mean_host_loads"], wh, label="Local Edge Only", color="#ef4444", alpha=0.85)
    ax3.bar(xh,      res_rr["mean_host_loads"],    wh, label="Round Robin",     color="#f59e0b", alpha=0.85)
    ax3.bar(xh + wh, res_smart["mean_host_loads"], wh, label="Load & Latency Aware", color="#0284c7")

    ax3.set_title("3. Hierarchical Load Balancing Across Hosts", fontsize=11, fontweight="bold")
    ax3.set_xticks(xh)
    ax3.set_xticklabels(host_labels)
    ax3.set_ylabel("Mean Queue Utilization (%)")
    ax3.set_ylim(0, 105)
    ax3.legend(fontsize=8.5)
    ax3.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Benchmark chart saved to: {output_file}")
    plt.show()


if __name__ == "__main__":
    workload_data = generate_5g_workload(NUM_TASKS, RANDOM_SEED)
    strategies = ["Local_Edge_Only", "Round_Robin", "Load_Latency_Aware"]
    sim_results = [run_policy_simulation(s, workload_data) for s in strategies]

    print_summary_table(sim_results)
    plot_benchmark_charts(workload_data, sim_results)
