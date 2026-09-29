# Cai Mep – Thi Vai Empty Container Digital Twin

A decision-support prototype for Empty Container Repositioning (ECR)
across the Cai Mep – Thi Vai port cluster, Vietnam.

## Project Architecture

The project combines two analytical layers:

### 1. Macro Planning – Step 08
- Public throughput reference for CMIT, TCIT and SSIT
- LOW / BASE / HIGH calibrated empty-container scenarios
- Planning allocation across three empty-container depots
- Geographic visualization of six network nodes

### 2. Operational Optimization – Steps 05–07
- Independent 90-day synthetic operational dataset
- Daily empty-container return, demand and inventory
- Road transport distance and cost assumptions
- Multi-period MILP repositioning optimization
- Sensitivity analysis

## Synthetic MILP Baseline Result

- Baseline shortage: 1,113 containers
- Optimized shortage: 0 containers
- Containers repositioned: 1,113
- Assumed ECR transport cost: approximately VND 1.838 billion

These results are generated from a synthetic operational case study
and should not be interpreted as observed performance of the
Cai Mep – Thi Vai port system.

## Technology

Python · pandas · PuLP/CBC · Streamlit · Plotly · Folium · ReportLab

## Purpose

The project explores how infrastructure knowledge, data analytics,
operations research and Digital Twin concepts can be integrated
into a practical maritime logistics decision-support workflow.

## Author

Minh Nguyen
