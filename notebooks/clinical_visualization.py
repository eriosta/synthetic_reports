"""
Clinical Visualization Module for Synthetic Reports

This module provides comprehensive clinical visualization functions for oncologists and radiologists
to analyze patient courses, treatment responses, and disease progression.

Author: SynthRad Contributors
License: MIT
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any


def plot_patient_course(pid: str, per_patient: Dict, jsonl_records: List[Dict], 
                       max_legend_items: int = 10, show_treatment: bool = False,
                       treatment_dates: Optional[List[datetime]] = None) -> None:
    """
    Plot comprehensive patient clinical course with enhanced visualization.
    
    This is the main function that provides a clean, professional visualization
    suitable for clinical presentations and tumor board discussions.
    
    Parameters:
    -----------
    pid : str
        Patient ID to plot
    per_patient : dict
        Dictionary mapping patient IDs to their case data
    jsonl_records : list
        List of JSONL records containing RECIST data
    max_legend_items : int, default=10
        Maximum number of items to show in legend
    show_treatment : bool, default=False
        Whether to show treatment timeline (requires treatment_dates)
    treatment_dates : list of datetime, optional
        List of treatment dates to overlay on timeline
        
    Returns:
    --------
    None
        Displays the plot and prints clinical summary
    """
    
    # --- Data preparation ---
    tl = sorted(per_patient[pid], key=lambda x: x[0])
    dates_cases = [d for d,_ in tl]
    stages = [c.tnm.stage_group for _,c in tl]
    T = [c.tnm.T for _,c in tl]; N = [c.tnm.N for _,c in tl]; M = [c.tnm.M for _,c in tl]
    stage_at = {d.strftime("%Y-%m-%d"): s for d,s in zip(dates_cases, stages)}

    # --- RECIST JSONL processing ---
    recs = sorted([r for r in jsonl_records if r["patient_id"] == pid], key=lambda r: r["study_date"])
    if not recs:
        raise ValueError(f"No JSONL records found for patient {pid}")
    
    dates = pd.to_datetime([r["study_date"] for r in recs])
    sld = [r["current_sld_mm"] for r in recs]
    baseline_sld = recs[0]["baseline_sld_mm"] or recs[0]["current_sld_mm"] or 0
    nadir_sld = min(sld)

    # --- Clinical calculations ---
    pr_threshold = baseline_sld * 0.7  # 30% decrease for PR
    pd_threshold = max(baseline_sld * 1.2, nadir_sld * 1.2)  # 20% increase for PD

    # --- Stage color mapping ---
    def stgcol(stage):
        s = (stage or "").upper().strip()
        if s.startswith("IV"):   return "purple"
        if s.startswith("III"):  return "red"
        if s.startswith("II"):   return "orange"
        if s.startswith("I"):    return "green"
        return "gray"
    
    cols = [stgcol(stage_at.get(r["study_date"], "")) for r in recs]
    stage_colors = {"I":"green","II":"orange","III":"red","IV":"purple"}

    # --- Lesion data collection ---
    all_ids = sorted({l["lesion_id"] for r in recs for l in r["lesions"]})
    base_targets = {l["lesion_id"] for l in recs[0]["lesions"] if l.get("target")}
    series = {lid:[
        float(next((l["size_mm_current"] for l in r["lesions"] if l["lesion_id"]==lid), np.nan))
        for r in recs
    ] for lid in all_ids}

    # --- New lesion detection ---
    seen, new_flags = set(), []
    for i, r in enumerate(recs):
        ids = {l["lesion_id"] for l in r["lesions"]}
        new_flags.append(i > 0 and len(ids - seen) > 0)
        seen |= ids

    # --- RECIST response calculation ---
    def recist_response(sld_now, new_lesion, baseline):
        if new_lesion:
            return "PD"
        if sld_now == 0:
            return "CR"
        if baseline and sld_now <= 0.7 * baseline:
            return "PR"
        if baseline and sld_now >= 1.2 * baseline and (sld_now - baseline) >= 5:
            return "PD"
        return "SD"

    responses = [recist_response(s, nf, baseline_sld) for s, nf in zip(sld, new_flags)]

    # --- Create visualization ---
    if show_treatment and treatment_dates:
        fig = plt.figure(figsize=(12, 10))
        gs = fig.add_gridspec(4, 1, height_ratios=[2.2, 1.8, 1.0, 0.6], hspace=0.3)
        ax1 = fig.add_subplot(gs[0])  # Lesions
        ax2 = fig.add_subplot(gs[1])  # SLD
        ax3 = fig.add_subplot(gs[2])  # TNM
        ax4 = fig.add_subplot(gs[3])  # Treatment
    else:
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9),
                                           gridspec_kw={"height_ratios":[2.2, 1.8, 1.0]},
                                           sharex=True)
    
    # Set clean background
    fig.patch.set_facecolor('white')
    for ax in [ax1, ax2, ax3] + ([ax4] if show_treatment and treatment_dates else []):
        ax.set_facecolor('white')

    # --- Plot 1: Lesion sizes ---
    _plot_lesions(ax1, series, dates, base_targets, max_legend_items, pid)

    # --- Plot 2: SLD with clinical markers ---
    target_lesions = _plot_sld(ax2, dates, sld, cols, baseline_sld, nadir_sld, 
                              responses, new_flags, stage_colors)

    # --- Plot 3: TNM staging ---
    _plot_tnm(ax3, dates, T, N, M, stages, stgcol)

    # --- Plot 4: Treatment timeline (if requested) ---
    if show_treatment and treatment_dates:
        _plot_treatment_timeline(ax4, treatment_dates)

    # --- Final formatting ---
    _format_axes([ax1, ax2, ax3] + ([ax4] if show_treatment and treatment_dates else []))

    plt.tight_layout(pad=2.0)
    plt.show()
    
    # --- Print clinical summary ---
    _print_clinical_summary(pid, recs, sld, baseline_sld, nadir_sld, responses, 
                           stages, new_flags, target_lesions)


def _plot_lesions(ax, series, dates, base_targets, max_legend_items, pid):
    """Plot individual lesion sizes with clean styling."""
    
    # Professional color palette
    primary_color = '#d62728'  # Professional red
    target_colors = ['#2ca02c', '#1f77b4', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
    non_target_color = '#a0a0a0'  # Muted gray
    
    for i, (lid, ys) in enumerate(series.items()):
        is_target = (lid in base_targets)
        is_primary = "primary" in lid.lower() or "tumor" in lid.lower()
        
        if is_primary:
            line_style = "-"
            line_width = 3
            alpha = 1.0
            marker_size = 8
            color = primary_color
            display_name = f'Primary Tumor'
        elif is_target:
            line_style = "-"
            line_width = 2
            alpha = 1.0
            marker_size = 6
            color = target_colors[i % len(target_colors)]
            display_name = f'{lid}'
        else:
            line_style = "--"
            line_width = 1.5
            alpha = 0.7
            marker_size = 4
            color = non_target_color
            display_name = f'{lid} (NT)'
        
        ax.plot(dates, ys, marker="o", lw=line_width, markersize=marker_size,
                label=display_name, ls=line_style, alpha=alpha, color=color, zorder=2)
    
    ax.set_ylabel("Lesion Size (mm)", fontsize=11, fontweight='normal')
    ax.set_title(f"Patient {pid} - Clinical Course", fontsize=13, fontweight='normal', pad=20)
    
    # Clean grid and legend
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles[:max_legend_items], labels[:max_legend_items],
                  ncol=2, fontsize=9, loc="upper left", frameon=False, 
                  columnspacing=1.5, handletextpad=0.5)


def _plot_sld(ax, dates, sld, cols, baseline_sld, nadir_sld, responses, new_flags, stage_colors):
    """Plot SLD with clinical reference lines and response labels."""
    
    # Main SLD line
    ax.plot(dates, sld, color="#2c3e50", marker="o", lw=2.5, markersize=8, zorder=2, label="SLD")
    ax.scatter(dates, sld, c=cols, s=120, zorder=3, edgecolors='white', linewidth=1.5)
    
    # Essential reference lines
    ax.axhline(y=baseline_sld, color='#1f77b4', linestyle='--', alpha=0.6, linewidth=1.5, 
               label=f'Baseline ({baseline_sld}mm)')
    ax.axhline(y=nadir_sld, color='#2ca02c', linestyle='--', alpha=0.6, linewidth=1.5, 
               label=f'Nadir ({nadir_sld}mm)')
    
    # RECIST response labels (only significant responses)
    for d, resp, val in zip(dates, responses, sld):
        if resp in ['PR', 'PD']:
            color = '#d62728' if resp == 'PD' else '#2ca02c' if resp == 'PR' else '#1f77b4'
            ax.text(d, val+8, resp, ha="center", fontsize=10, weight="normal", color=color,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9, 
                           edgecolor=color, linewidth=0.5))
    
    # Subtle new lesion indicators
    for d, nf in zip(dates, new_flags):
        if nf: 
            ax.axvline(d, color="#9467bd", alpha=0.2, lw=8, zorder=1)
    
    ax.set_ylabel("SLD (mm)", fontsize=11, fontweight='normal')
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Combined legend
    legend_handles = []
    legend_labels = []
    
    # Add SLD line
    legend_handles.append(plt.Line2D([0],[0], color="#2c3e50", lw=2.5, marker="o", markersize=6))
    legend_labels.append("SLD")
    
    # Add reference lines
    legend_handles.append(plt.Line2D([0],[0], color='#1f77b4', linestyle='--', lw=1.5))
    legend_labels.append(f'Baseline ({baseline_sld}mm)')
    legend_handles.append(plt.Line2D([0],[0], color='#2ca02c', linestyle='--', lw=1.5))
    legend_labels.append(f'Nadir ({nadir_sld}mm)')
    
    # Add stage colors
    for k,c in stage_colors.items():
        legend_handles.append(plt.Line2D([0],[0], lw=0, marker="o", color="w", 
                                        markerfacecolor=c, markersize=8))
        legend_labels.append(f'Stage {k}')
    
    ax.legend(legend_handles, legend_labels, loc="upper left", frameon=False, 
              fontsize=8, ncol=2, columnspacing=1.0, handletextpad=0.5)
    
    return []  # Return empty list for target_lesions (would need to be calculated)


def _plot_tnm(ax, dates, T, N, M, stages, stgcol):
    """Plot TNM staging with overall stage groups."""
    
    def strip(labels, y, color):
        ax.scatter(dates, [y]*len(dates), c=color, s=400, marker="s", 
                  edgecolors='white', linewidth=1)
        for d, lab in zip(dates, labels):
            ax.text(d, y, lab, ha="center", va="center", fontsize=10, 
                   color="white", weight="normal")
    
    ax.set_yticks([3,2,1]); ax.set_yticklabels(["T","N","M"])
    strip(T, 3, "#2A9D8F"); strip(N, 2, "#E76F51"); strip(M, 1, "#264653")
    ax.set_ylim(0.5, 3.5)
    ax.set_ylabel("TNM Staging", fontsize=11, fontweight='normal')
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Stage group labels
    for i, (d, stage) in enumerate(zip(dates, stages)):
        ax.text(d, 3.8, f"Stage {stage}", ha="center", fontsize=9, weight="normal", 
               color=stgcol(stage), bbox=dict(boxstyle="round,pad=0.15", 
               facecolor='white', alpha=0.9, edgecolor='none'))


def _plot_treatment_timeline(ax, treatment_dates):
    """Plot treatment timeline overlay."""
    
    ax.barh(0, [1]*len(treatment_dates), left=treatment_dates, height=0.5, 
           color='lightblue', alpha=0.7, label='Treatment')
    ax.set_ylim(-0.5, 0.5)
    ax.set_ylabel("Treatment", fontsize=11, fontweight='normal')
    ax.set_yticks([])


def _format_axes(axes):
    """Apply consistent formatting to all axes."""
    
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)


def _print_clinical_summary(pid, recs, sld, baseline_sld, nadir_sld, responses, 
                           stages, new_flags, target_lesions):
    """Print concise clinical summary."""
    
    print(f"\n{'='*50}")
    print(f"CLINICAL SUMMARY - Patient {pid}")
    print(f"{'='*50}")
    print(f"Studies: {len(recs)} | Baseline SLD: {baseline_sld}mm | Nadir: {nadir_sld}mm | Latest: {sld[-1]}mm")
    
    # Best response
    best_response = "SD"
    if "CR" in responses:
        best_response = "CR"
    elif "PR" in responses:
        best_response = "PR"
    elif "PD" in responses:
        best_response = "PD"
    
    print(f"Best Response: {best_response} | Current Stage: {stages[-1] if stages else 'Unknown'}")
    
    # Key clinical events
    key_events = []
    for i, (r, s, resp, stage) in enumerate(zip(recs, sld, responses, stages)):
        if resp == "PR":
            key_events.append(f"PR at {r['study_date']} (SLD: {s}mm)")
        elif resp == "PD":
            key_events.append(f"PD at {r['study_date']} (SLD: {s}mm)")
        elif i > 0 and new_flags[i]:
            key_events.append(f"New lesions at {r['study_date']}")
    
    if key_events:
        print(f"Key Events: {' | '.join(key_events)}")


# --- Convenience functions for different use cases ---

def plot_simple_course(pid: str, per_patient: Dict, jsonl_records: List[Dict]) -> None:
    """
    Simple version with just the essential clinical visualization.
    """
    plot_patient_course(pid, per_patient, jsonl_records, max_legend_items=8)


def plot_with_treatment(pid: str, per_patient: Dict, jsonl_records: List[Dict], 
                       treatment_dates: List[datetime]) -> None:
    """
    Full visualization including treatment timeline.
    """
    plot_patient_course(pid, per_patient, jsonl_records, show_treatment=True, 
                       treatment_dates=treatment_dates)


def plot_all_patients(per_patient: Dict, jsonl_records: List[Dict], 
                     max_patients: int = 5) -> None:
    """
    Plot multiple patients for cohort analysis.
    """
    patient_ids = sorted(per_patient.keys())[:max_patients]
    
    for pid in patient_ids:
        print(f"\n{'='*60}")
        print(f"PLOTTING PATIENT: {pid}")
        print(f"{'='*60}")
        plot_patient_course(pid, per_patient, jsonl_records)


# --- Example usage and documentation ---

def create_example_treatment_dates() -> List[datetime]:
    """Create example treatment dates for demonstration."""
    return [
        datetime(2024, 8, 15),   # Start chemotherapy
        datetime(2024, 9, 15),   # Cycle 2
        datetime(2024, 10, 15),  # Cycle 3
        datetime(2024, 11, 15),  # Cycle 4
        datetime(2025, 1, 10),   # Radiation start
        datetime(2025, 2, 10),   # Radiation end
        datetime(2025, 3, 15),   # New treatment start
    ]


# --- Module documentation ---
__doc__ = """
Clinical Visualization Module

This module provides comprehensive clinical visualization functions for analyzing
patient courses, treatment responses, and disease progression in oncology.

Main Functions:
- plot_patient_course(): Main comprehensive visualization
- plot_simple_course(): Simplified version
- plot_with_treatment(): Includes treatment timeline
- plot_all_patients(): Cohort analysis

Example Usage:
    from clinical_visualization import plot_patient_course
    
    # Basic usage
    plot_patient_course(pid, per_patient, jsonl_records)
    
    # With treatment timeline
    treatment_dates = [datetime(2024, 8, 15), datetime(2024, 9, 15)]
    plot_patient_course(pid, per_patient, jsonl_records, 
                       show_treatment=True, treatment_dates=treatment_dates)
"""
