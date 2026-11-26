"""
5G MEC Host Selection Simulation (ETSI GS MEC 003 / 3GPP 5G Core Architecture)
Author: Mai Cuong Tho (thomc@ntu.edu.vn)
Description:
    Simulates real-time task offloading and MEC Host selection in a 5G heterogeneous
    network environment. Models 5G NR radio uplink delay, N3/N9 backhaul penalty
    via 5G Core UPF (Local Breakout), MEC Host queuing delay, CPU execution delay,
    and V2X mobility handover across gNB cells.
"""

import copy
import random
import numpy as np
import matplotlib.pyplot as plt


def generate_5g_workload(num_tasks: int = 80, seed: int = 42) -> list[dict]:
    """Generates a chronological workload of 5G UE task requests with V2X handover."""
    random.seed(seed)
    workload = []
    current_time = 0.0

    ue_profiles = [
        {"type": "5G Smartphone", "gnb": "gNB-01", "uplink_mbps": 120.0},
        {"type": "5G Smart Camera", "gnb": "gNB-02", "uplink_mbps": 95.0},
        {"type": "Autonomous V2X", "gnb": "gNB-01", "uplink_mbps": 150.0},
    ]

    for idx in range(num_tasks):
        inter_arrival = random.uniform(0.08, 0.32)
        current_time += inter_arrival

        ue = copy.deepcopy(random.choice(ue_profiles))
        # Simulate V2X mobility handover from gNB-01 to gNB-02 after task 35
        if ue["type"] == "Autonomous V2X" and idx >= 35:
            ue["gnb"] = "gNB-02"
            ue["uplink_mbps"] = 135.0

        data_size_mb = random.uniform(2.0, 12.0)      # D_i (Megabytes)
        compute_cycles = random.randint(25, 65)        # C_i (Megacycles)

        workload.append({
            "task_id": idx + 1,
            "inter_arrival": inter_arrival,
            "timestamp": current_time,
            "ue_type": ue["type"],
            "connected_gnb": ue["gnb"],
            "uplink_mbps": ue["uplink_mbps"],
            "data_mb": data_size_mb,
            "cycles": compute_cycles,
        })
    return workload


def get_5g_infrastructure() -> tuple[list[dict], dict[tuple[str, str], float]]:
    """Initializes heterogeneous ETSI MEC Hosts and N3/N9 backhaul latency matrix."""
    mec_hosts = [
        {
            "id": "MEC-1",
            "name": "MEC Host 1\n(gNB-01 Local)",
            "site_gnb": "gNB-01",
            "cpu_capacity": 100.0,
            "queue": 0.0,
            "tasks_served": 0,
        },
        {
            "id": "MEC-2",
            "name": "MEC Host 2\n(gNB-02 Local)",
            "site_gnb": "gNB-02",
            "cpu_capacity": 65.0,
            "queue": 0.0,
            "tasks_served": 0,
        },
        {
            "id": "MEC-3",
            "name": "MEC Host 3\n(Regional Edge)",
            "site_gnb": "Regional",
            "cpu_capacity": 85.0,
            "queue": 0.0,
            "tasks_served": 0,
        },
    ]

    # Backhaul & UPF routing latency (seconds) from source gNB to target MEC Host
    backhaul_matrix = {
        ("gNB-01", "MEC-1"): 0.005,  # Local breakout at gNB-01 (5 ms)
        ("gNB-01", "MEC-2"): 0.045,  # Cross-site N9 routing via UPF (45 ms)
        ("gNB-01", "MEC-3"): 0.025,  # Regional aggregation site (25 ms)
        ("gNB-02", "MEC-1"): 0.045,  # Cross-site N9 routing via UPF (45 ms)
        ("gNB-02", "MEC-2"): 0.005,  # Local breakout at gNB-02 (5 ms)
        ("gNB-02", "MEC-3"): 0.025,  # Regional aggregation site (25 ms)
    }
    return mec_hosts, backhaul_matrix


def compute_total_5g_latency(
    task: dict, host: dict, backhaul_matrix: dict[tuple[str, str], float]
) -> float:
    """
    Computes end-to-end 5G MEC latency:
        T_total = T_radio_5G + T_backhaul + T_queue + T_exec
    """
    # Convert MB to Megabits (* 8) for 5G NR uplink transmission time
    t_radio = (task["data_mb"] * 8.0) / task["uplink_mbps"]
    t_backhaul = backhaul_matrix[(task["connected_gnb"], host["id"])]
    t_queue = host["queue"] / host["cpu_capacity"]
    t_exec = task["cycles"] / host["cpu_capacity"]
    return t_radio + t_backhaul + t_queue + t_exec


def select_mec_host(
    strategy: str,
    task: dict,
    mec_hosts: list[dict],
    backhaul_matrix: dict[tuple[str, str], float],
    rr_idx: int,
) -> dict:
    """MEO Control Plane decision policy for selecting target MEC Host."""
    if strategy == "Round_Robin":
        return mec_hosts[rr_idx % len(mec_hosts)]

    if strategy == "Nearest_Local_MEC":
        # Always binds UE to the co-located MEC Host at its serving gNB
        for h in mec_hosts:
            if h["site_gnb"] == task["connected_gnb"]:
                return h
        return mec_hosts[0]

    if strategy == "MEO_Joint_QoS_Load":
        return min(
            mec_hosts,
            key=lambda h: compute_total_5g_latency(task, h, backhaul_matrix),
        )

    raise ValueError(f"Unknown orchestration strategy: {strategy}")


def run_5g_simulation(
    strategy: str, workload: list[dict]
) -> dict:
    """Executes real-time discrete-event simulation for a given MEO policy."""
    mec_hosts, backhaul_matrix = get_5g_infrastructure()
    delays = []
    load_traces = {h["name"]: [] for h in mec_hosts}

    for idx, task in enumerate(workload):
        # 1. Advance real-time clock: MEC Hosts process queued workloads
        for h in mec_hosts:
            processed = h["cpu_capacity"] * task["inter_arrival"]
            h["queue"] = max(0.0, h["queue"] - processed)

        # 2. MEO Control Plane selects optimal MEC Host
        chosen = select_mec_host(strategy, task, mec_hosts, backhaul_matrix, idx)

        # 3. Record end-to-end latency and enqueue new task
        latency = compute_total_5g_latency(task, chosen, backhaul_matrix)
        delays.append(latency)

        chosen["queue"] += task["cycles"]
        chosen["tasks_served"] += 1

        for h in mec_hosts:
            load_traces[h["name"]].append(h["queue"] / h["cpu_capacity"])

    avg_loads = [float(np.mean(load_traces[h["name"]])) for h in mec_hosts]
    return {
        "delays": delays,
        "avg_delay": float(np.mean(delays)),
        "max_delay": float(np.max(delays)),
        "avg_loads": avg_loads,
        "load_std": float(np.std(avg_loads)),
        "hosts": mec_hosts,
    }


def plot_5g_results(workload: list[dict], results: dict[str, dict]) -> None:
    """Generates a 3-panel comparative visualization for 5G MEC Host Selection."""
    timestamps = [t["timestamp"] for t in workload]
    handover_time = workload[35]["timestamp"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle(
        "5G MEC HOST SELECTION PERFORMANCE EVALUATION (ETSI GS MEC 003 / 3GPP 5G CORE)",
        fontsize=14,
        fontweight="bold",
    )

    # Panel 1: Real-time End-to-End Latency with V2X Handover Marker
    ax1.plot(
        timestamps,
        results["Round_Robin"]["delays"],
        label="Round Robin",
        color="#f28e2b",
        linestyle="-.",
        alpha=0.75,
    )
    ax1.plot(
        timestamps,
        results["Nearest_Local_MEC"]["delays"],
        label="Nearest Local MEC",
        color="#e15759",
        linestyle="--",
        alpha=0.75,
    )
    ax1.plot(
        timestamps,
        results["MEO_Joint_QoS_Load"]["delays"],
        label="MEO Joint QoS & Load",
        color="#2b83ba",
        linewidth=2.3,
    )
    ax1.axvline(
        handover_time,
        color="#64748b",
        linestyle=":",
        linewidth=1.5,
        label="V2X Handover (gNB-01 -> gNB-02)",
    )
    ax1.set_title("1. Real-Time Latency & V2X Handover", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Simulation Time (Seconds)")
    ax1.set_ylabel("End-to-End Latency (Seconds)")
    ax1.legend(fontsize=8.5)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Panel 2: System-Wide Average Latency Comparison
    labels = ["Round Robin", "Nearest Local\nMEC", "MEO Joint\nQoS & Load"]
    avgs = [
        results["Round_Robin"]["avg_delay"],
        results["Nearest_Local_MEC"]["avg_delay"],
        results["MEO_Joint_QoS_Load"]["avg_delay"],
    ]
    bars = ax2.bar(labels, avgs, color=["#f28e2b", "#e15759", "#2b83ba"], width=0.45)
    ax2.set_title("2. Average End-to-End Latency", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Average Latency (Seconds)")
    ax2.set_ylim(0, max(avgs) * 1.25)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars:
        yval = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            yval + 0.02,
            f"{yval:.3f}s",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Panel 3: Load Balancing across ETSI MEC Hosts
    host_names = [h["name"] for h in results["MEO_Joint_QoS_Load"]["hosts"]]
    x = np.arange(len(host_names))
    w = 0.25

    ax3.bar(
        x - w,
        results["Round_Robin"]["avg_loads"],
        w,
        label="Round Robin",
        color="#f28e2b",
        alpha=0.85,
    )
    ax3.bar(
        x,
        results["Nearest_Local_MEC"]["avg_loads"],
        w,
        label="Nearest Local MEC",
        color="#e15759",
        alpha=0.85,
    )
    ax3.bar(
        x + w,
        results["MEO_Joint_QoS_Load"]["avg_loads"],
        w,
        label="MEO Joint QoS & Load",
        color="#2b83ba",
    )
    ax3.set_title("3. Load Balancing Across MEC Hosts", fontsize=11, fontweight="bold")
    ax3.set_xticks(x)
    ax3.set_xticklabels(host_names, fontsize=9)
    ax3.set_ylabel("Mean Queuing Delay (Seconds)")
    ax3.legend(fontsize=8.5)
    ax3.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig("5g_mec_simulation_results.png", dpi=300)
    plt.show()


if __name__ == "__main__":
    workload_data = generate_5g_workload(num_tasks=80, seed=42)
    strategies = ["Round_Robin", "Nearest_Local_MEC", "MEO_Joint_QoS_Load"]
    sim_results = {s: run_5g_simulation(s, workload_data) for s in strategies}

    print("=" * 72)
    print("5G MEC HOST SELECTION SIMULATION SUMMARY (Author: Mai Cuong Tho)")
    print("=" * 72)
    print(f"{'Strategy':<22} | {'Avg Latency':<12} | {'Max Latency':<12} | {'Load StdDev':<12}")
    print("-" * 72)
    for s in strategies:
        r = sim_results[s]
        print(
            f"{s:<22} | {r['avg_delay']:>10.3f}s | {r['max_delay']:>10.3f}s | {r['load_std']:>10.4f}s"
        )
    print("=" * 72)

    plot_5g_results(workload_data, sim_results)
