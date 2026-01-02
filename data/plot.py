"""
Visualize gas costs relations
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

sns.set_style("whitegrid")

def load_data(filepath):
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    df = pd.DataFrame(data)
    
    if 'gas_exec_measured' in df.columns and 'gas_exec' not in df.columns:
        df['gas_exec'] = df['gas_exec_measured']
    
    return df

def create_combined_plot(df, output_path):
    
    fig = plt.figure(figsize=(20, 16))
     
    # Min and Max Gas Auctions 
    ax0 = plt.subplot(2, 3, 1)
    x = range(len(df))
    y = df['gas_total'].values

    ax0.plot(x, y, color='steelblue', linewidth=1.5, alpha=0.8)
    ax0.fill_between(x, y, alpha=0.3, color='steelblue')
    min_idx = df['gas_total'].idxmin()
    max_idx = df['gas_total'].idxmax()

    min_gas = df.loc[min_idx, 'gas_total']
    max_gas = df.loc[max_idx, 'gas_total']
    min_auction = df.loc[min_idx, 'auction_actual_id']
    max_auction = df.loc[max_idx, 'auction_actual_id']

    ax0.scatter([min_idx], [min_gas], color='green', s=200, zorder=5, 
               edgecolor='green', linewidth=2, marker='o', label='Min')
    ax0.scatter([max_idx], [max_gas], color='red', s=200, zorder=5, 
               edgecolor='red', linewidth=2, marker='o', label='Max')

    ax0.annotate(f'Min: {min_gas:,.0f}\nAuction {min_auction}', 
                xy=(min_idx, min_gas), 
                xytext=(10, 20), textcoords='offset points')

    ax0.annotate(f'Max: {max_gas:,.0f}\nAuction {max_auction}', 
                xy=(max_idx, max_gas), 
                xytext=(-10, -40), textcoords='offset points')

    mean_gas = df['gas_total'].mean()
    ax0.axhline(mean_gas, color='orange', linestyle='--', linewidth=2, 
               alpha=0.7, label=f'Mean: {mean_gas:,.0f}')

    ax0.set_xlabel('Auction Sequence', fontsize=11)
    ax0.set_ylabel('Total Gas Cost', fontsize=11)
    ax0.set_title('Gas Cost Across Auctions', fontsize=12, fontweight='bold')
    ax0.legend(fontsize=9, loc='upper right')
    ax0.grid(True, alpha=0.3)
    
    # Gas vs Solutions
    ax1 = plt.subplot(2, 3, 2)
    ax1.scatter(df['num_solutions'], df['gas_total'], alpha=0.6, s=50, color='steelblue')
    ax1.set_xlabel('Number of Solutions', fontsize=11)
    ax1.set_ylabel('Total Gas Cost', fontsize=11)
    ax1.set_title('Gas Cost vs Number of Solutions', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    z = np.polyfit(df['num_solutions'], df['gas_total'], 1)
    p = np.poly1d(z)
    ax1.plot(df['num_solutions'], p(df['num_solutions']), 
             "r--", alpha=0.8, linewidth=2, label=f'y={z[0]:.0f}x+{z[1]:.0f}')
    ax1.legend(fontsize=9)
    
    # Gas vs Trades
    ax2 = plt.subplot(2, 3, 3)
    scatter = ax2.scatter(df['num_trades'], df['gas_total'], 
                         c=df['num_solutions'], cmap='viridis', 
                         alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    ax2.set_xlabel('Number of Trades', fontsize=11)
    ax2.set_ylabel('Total Gas Cost', fontsize=11)
    ax2.set_title('Gas Cost vs Number of Trades', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('Solutions', fontsize=10)
    
    z2 = np.polyfit(df['num_trades'], df['gas_total'], 1)
    p2 = np.poly1d(z2)
    ax2.plot(df['num_trades'], p2(df['num_trades']), 
             "r--", alpha=0.8, linewidth=2)
    
    # Gas vs Solvers
    ax3 = plt.subplot(2, 3, 4)
    ax3.scatter(df['num_solvers'], df['gas_total'], alpha=0.6, s=50, color='lightcoral')
    ax3.set_xlabel('Number of Solvers', fontsize=11)
    ax3.set_ylabel('Total Gas Cost', fontsize=11)
    ax3.set_title('Gas Cost vs Number of Solvers', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    z3 = np.polyfit(df['num_solvers'], df['gas_total'], 1)
    p3 = np.poly1d(z3)
    ax3.plot(df['num_solvers'], p3(df['num_solvers']), 
             "r--", alpha=0.8, linewidth=2, label=f'y={z3[0]:.0f}x+{z3[1]:.0f}')
    ax3.legend(fontsize=9)
    
    # Gas Components Breakdown
    ax4 = plt.subplot(2, 3, 5)
    
    # Filter to only Forge results (which have gas_exec)
    df_forge = df[df['gas_exec'].notna()].copy()
    
    if len(df_forge) > 0:
        df_forge_sorted = df_forge.sort_values('num_solutions').reset_index(drop=True)
        ax4.fill_between(range(len(df_forge_sorted)), 
                         0, df_forge_sorted['gas_intrinsic'], 
                         label='Intrinsic (21k)', alpha=0.7, color='#99ff99')
        ax4.fill_between(range(len(df_forge_sorted)), 
                         df_forge_sorted['gas_intrinsic'], 
                         df_forge_sorted['gas_intrinsic'] + df_forge_sorted['gas_calldata'],
                         label='Calldata', alpha=0.7, color='#66b3ff')
        ax4.fill_between(range(len(df_forge_sorted)), 
                         df_forge_sorted['gas_intrinsic'] + df_forge_sorted['gas_calldata'],
                         df_forge_sorted['gas_total'],
                         label='Execution', alpha=0.7, color='#ff9999')
        
        ax4.set_xlabel('Auction Index (sorted)', fontsize=11)
        ax4.set_ylabel('Gas Cost', fontsize=11)
        ax4.set_title('Gas Components Breakdown', fontsize=12, fontweight='bold')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'No Forge data available\nfor gas breakdown', 
                ha='center', va='center', fontsize=12, transform=ax4.transAxes)
        ax4.set_title('Gas Components Breakdown', fontsize=12, fontweight='bold')
    
    # Gas per Solution
    ax5 = plt.subplot(2, 3, 6)
    df['gas_per_solution'] = df['gas_total'] / df['num_solutions']
    
    ax5.hist(df['gas_per_solution'], bins=40, edgecolor='black', alpha=0.7, color='mediumpurple')
    ax5.set_xlabel('Gas Cost per Solution', fontsize=11)
    ax5.set_ylabel('Frequency', fontsize=11)
    ax5.set_title('Distribution of Gas per Solution', fontsize=12, fontweight='bold')
    ax5.axvline(df['gas_per_solution'].mean(), color='red', 
                linestyle='--', linewidth=2, 
                label=f'Mean: {df["gas_per_solution"].mean():.0f}')
    ax5.axvline(df['gas_per_solution'].median(), color='green', 
                linestyle='--', linewidth=2, 
                label=f'Median: {df["gas_per_solution"].median():.0f}')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f" Saved combined plot to: {output_path}")

def print_summary_statistics(df):
    """summary statistics."""
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    print(f"\nTotal Auctions: {len(df)}")
    print(f"\nGas Total:")
    print(f"  Mean:   {df['gas_total'].mean():,.0f}")
    print(f"  Median: {df['gas_total'].median():,.0f}")
    print(f"  Min:    {df['gas_total'].min():,.0f}")
    print(f"  Max:    {df['gas_total'].max():,.0f}")
    
    print(f"\nSolutions per Auction:")
    print(f"  Mean:   {df['num_solutions'].mean():.1f}")
    print(f"  Median: {df['num_solutions'].median():.0f}")
    
    print(f"\nTrades per Auction:")
    print(f"  Mean:   {df['num_trades'].mean():.1f}")
    print(f"  Median: {df['num_trades'].median():.0f}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="auction_gas_data.jsonl")
    parser.add_argument("--output", default="gas_analysis.png")
    args = parser.parse_args()
    
    print(f"Loading data from {args.input}...")
    df = load_data(args.input)
    print(f"Loaded {len(df)} auctions\n")
    
    print_summary_statistics(df)
    
    create_combined_plot(df, args.output)
    
    print(f"\n Done View: {args.output}")

if __name__ == "__main__":
    main()