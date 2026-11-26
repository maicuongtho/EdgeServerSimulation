"""
=============================================================================
Title: Real-Time Task Offloading Simulation in Heterogeneous Edge Computing
       (Load and Latency-Aware Scheduling Algorithm)
Author: Mai Cuong Tho (thomc@ntu.edu.vn)
Description:
    Standalone Python simulation comparing three task offloading strategies:
    1. Random Offloading (Baseline 1)
    2. Round Robin Scheduling (Baseline 2)
    3. Load & Latency-Aware Optimal Offloading (Proposed Algorithm)

    The simulation models real-time queue depletion between task arrivals,
    computes end-to-end latency (transmission + queue wait + CPU execution),
    and evaluates server load balancing across heterogeneous edge nodes.
=============================================================================
"""

import random
import copy
import numpy as np
import matplotlib.pyplot as plt


def generate_workload(num_tasks: int = 60, seed: int = 42) -> list:
    """
    Generates a reproducible stochastic workload of tasks arriving over time.
    
    Args:
        num_tasks (int): Total number of tasks to simulate.
        seed (int): Random seed for reproducibility.
        
    Returns:
        list[dict]: List of task events with arrival delta, timestamp, and compute size.
    """
    random.seed(seed)
    workload = []
    current_time = 0.0

    for task_id in range(1, num_tasks + 1):
        # Inter-arrival time in seconds (bursty traffic pattern)
        time_passed = random.uniform(0.08, 0.35)
        current_time += time_passed
        
        # Computational complexity (in Megacycles / abstract compute units)
        task_size = random.randint(25, 65)
        
        workload.append({
            "id": task_id,
            "time_passed": time_passed,
            "timestamp": current_time,
            "size": task_size
        })
    return workload


def get_initial_servers() -> list:
    """
    Initializes a heterogeneous cluster of 3 Edge Servers.
    
    Returns:
        list[dict]: Server configurations with CPU capacity, network delay, and queue.
    """
    return [
        {"name": "Edge Server 1\n(High CPU, Far)",  "cpu": 100.0, "net_delay": 0.50, "queue": 0.0, "assigned": 0},
        {"name": "Edge Server 2\n(Mid CPU, Near)",  "cpu": 60.0,  "net_delay": 0.10, "queue": 0.0, "assigned": 0},
        {"name": "Edge Server 3\n(Low CPU, Local)", "cpu": 40.0,  "net_delay": 0.05, "queue": 0.0, "assigned": 0}
    ]


def select_optimal_server(task_size: float, servers: list) -> tuple:
    """
    Core Proposed Algorithm: Load and Latency-Aware Task Offloading.
    Evaluates the expected end-to-end latency on every available edge server
    and selects the node minimizing total completion time.
    
    Time Complexity: O(M), where M is the number of edge servers.
    
    Args:
        task_size (float): Computational demand (C_i) of the incoming task.
        servers (list[dict]): Current state of all edge servers.
        
    Returns:
        tuple: (selected_server_dict, predicted_total_delay)
    """
    best_server = None
    min_total_delay = float('inf')

    for server in servers:
        # 1. Queueing delay reflecting current server load: Q_j(t) / f_j
        wait_time = server["queue"] / server["cpu"]
        
        # 2. Execution time on target CPU: C_i / f_j
        exec_time = task_size / server["cpu"]
        
        # 3. End-to-end latency: T_net + T_wait + T_exec
        total_delay = server["net_delay"] + wait_time + exec_time

        if total_delay < min_total_delay:
            min_total_delay = total_delay
            best_server = server

    return best_server, min_total_delay


def run_simulation(strategy: str, workload: list, seed: int = 42) -> dict:
    """
    Executes the real-time discrete-event simulation for a given scheduling strategy.
    
    Args:
        strategy (str): 'Random', 'Round_Robin', or 'Load_Latency_Aware'.
        workload (list[dict]): Generated sequence of incoming tasks.
        seed (int): Random seed for baseline random choices.
        
    Returns:
        dict: Performance metrics including task delays, average server loads,
              mean latency, and load imbalance standard deviation.
    """
    random.seed(seed)
    servers = get_initial_servers()
    delays = []
    load_history = {s["name"]: [] for s in servers}

    for idx, task in enumerate(workload):
        # Step 1: Real-time queue depletion over elapsed time delta
        for s in servers:
            processed_work = s["cpu"] * task["time_passed"]
            s["queue"] = max(0.0, s["queue"] - processed_work)

        # Step 2: Offloading decision based on selected policy
        if strategy == "Random":
            selected = random.choice(servers)
        elif strategy == "Round_Robin":
            selected = servers[idx % len(servers)]
        elif strategy == "Load_Latency_Aware":
            selected, _ = select_optimal_server(task["size"], servers)
        else:
            raise ValueError(f"Unknown scheduling strategy: {strategy}")

        # Step 3: Compute actual end-to-end delay for the assigned task
        actual_delay = selected["net_delay"] + (selected["queue"] + task["size"]) / selected["cpu"]
        delays.append(actual_delay)

        # Step 4: Enqueue task onto the chosen edge server
        selected["queue"] += task["size"]
        selected["assigned"] += 1

        # Step 5: Record instantaneous load (wait time in seconds) across all nodes
        for s in servers:
            load_history[s["name"]].append(s["queue"] / s["cpu"])

    avg_server_loads = [float(np.mean(load_history[s["name"]])) for s in servers]
    
    return {
        "strategy": strategy,
        "delays": delays,
        "mean_delay": float(np.mean(delays)),
        "max_delay": float(np.max(delays)),
        "avg_server_loads": avg_server_loads,
        "load_std_dev": float(np.std(avg_server_loads)),
        "task_distribution": [s["assigned"] for s in servers]
    }


def plot_comparison_results(workload: list, results: dict, save_path: str = None) -> None:
    """
    Generates a 3-panel comparative visualization:
    1. Real-time end-to-end latency timeline.
    2. System-wide average latency bar chart.
    3. Per-server load balancing grouped bar chart.
    """
    timestamps = [t["timestamp"] for t in workload]
    res_rand = results["Random"]
    res_rr = results["Round_Robin"]
    res_opt = results["Load_Latency_Aware"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle(
        "EDGE COMPUTING TASK OFFLOADING: LATENCY & LOAD BALANCING EVALUATION",
        fontsize=14, fontweight='bold'
    )

    # Panel 1: Real-Time Latency Timeline
    ax1.plot(timestamps, res_rand["delays"], label="Random", color="#e15759", alpha=0.55, linestyle="--")
    ax1.plot(timestamps, res_rr["delays"], label="Round Robin", color="#f28e2b", alpha=0.8, linestyle="-.")
    ax1.plot(timestamps, res_opt["delays"], label="Proposed (Load & Latency)", color="#2b83ba", linewidth=2.2)
    ax1.set_title("1. Real-Time End-to-End Latency", fontsize=11, fontweight='bold')
    ax1.set_xlabel("Simulation Time (s)")
    ax1.set_ylabel("Total Latency (s)")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Panel 2: Average System Latency
    labels = ["Random", "Round Robin", "Proposed\n(Load & Latency)"]
    means = [res_rand["mean_delay"], res_rr["mean_delay"], res_opt["mean_delay"]]
    bars = ax2.bar(labels, means, color=["#e15759", "#f28e2b", "#2b83ba"], width=0.45)
    ax2.set_title("2. Average System Latency", fontsize=11, fontweight='bold')
    ax2.set_ylabel("Mean Latency (s)")
    ax2.set_ylim(0, max(means) * 1.25)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for i, bar in enumerate(bars):
        yval = bar.get_height()
        if i == 2:
            reduction = (res_rr["mean_delay"] - yval) / res_rr["mean_delay"] * 100
            text = f"{yval:.2f}s\n(-{reduction:.1f}% vs RR)"
        else:
            text = f"{yval:.2f}s"
        ax2.text(bar.get_x() + bar.get_width() / 2, yval + 0.03, text,
                 ha="center", va="bottom", fontweight="bold", fontsize=9.5)

    # Panel 3: Server Load Balancing
    server_names = [s["name"] for s in get_initial_servers()]
    x = np.arange(len(server_names))
    width = 0.25

    ax3.bar(x - width, res_rand["avg_server_loads"], width, label="Random", color="#e15759", alpha=0.85)
    ax3.bar(x,         res_rr["avg_server_loads"],   width, label="Round Robin", color="#f28e2b", alpha=0.85)
    ax3.bar(x + width, res_opt["avg_server_loads"],  width, label="Proposed (Load & Latency)", color="#2b83ba")

    ax3.set_title("3. Load Balancing (Avg Queue Wait Time)", fontsize=11, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(server_names, fontsize=9)
    ax3.set_ylabel("Mean Wait Time (s)")
    ax3.legend()
    ax3.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"[INFO] Figure saved to: {save_path}")
    plt.show()


def main():
    print("=" * 72)
    print("EDGE COMPUTING TASK OFFLOADING SIMULATION (LOAD & LATENCY-AWARE)")
    print("Author: Mai Cuong Tho (thomc@ntu.edu.vn)")
    print("=" * 72)

    num_tasks = 60
    seed = 42
    workload = generate_workload(num_tasks=num_tasks, seed=seed)

    strategies = ["Random", "Round_Robin", "Load_Latency_Aware"]
    results = {}

    for strat in strategies:
        results[strat] = run_simulation(strategy=strat, workload=workload, seed=seed)

    print(f"\n{'Strategy':<22} | {'Mean Delay':<11} | {'Max Delay':<10} | {'Load StdDev':<12} | {'Tasks [S1, S2, S3]'}")
    print("-" * 78)
    for strat in strategies:
        r = results[strat]
        print(f"{strat:<22} | {r['mean_delay']:>8.3f} s  | {r['max_delay']:>7.3f} s  | "
              f"{r['load_std_dev']:>9.3f} s  | {r['task_distribution']}")

    rr_mean = results["Round_Robin"]["mean_delay"]
    opt_mean = results["Load_Latency_Aware"]["mean_delay"]
    improvement = (rr_mean - opt_mean) / rr_mean * 100
    print("-" * 78)
    print(f"[SUMMARY] Proposed algorithm reduces mean latency by {improvement:.2f}% compared to Round Robin.\n")

    plot_comparison_results(workload, results)


if __name__ == "__main__":
    main()
