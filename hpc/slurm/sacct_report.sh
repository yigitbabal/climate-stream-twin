#!/bin/bash
# Scheduler-side metrics for one run: queue wait, runtime, CPU time and peak memory per job.
#   ./hpc/slurm/sacct_report.sh <logdir>
set -euo pipefail
LOGDIR="${1:?usage: sacct_report.sh <logdir>}"
IDS=$(paste -sd, "$LOGDIR/job_ids.txt")
sacct -j "$IDS" -P -n \
  --format=JobID,JobName,State,ExitCode,Submit,Start,End,Elapsed,TotalCPU,MaxRSS \
  | tee "$LOGDIR/sacct.psv" \
  | awk -F'|' 'BEGIN{printf "%-22s %-18s %-10s %-9s %-10s\n","job","name","state","elapsed","maxrss"}
               $1 !~ /\.(extern)$/ {printf "%-22s %-18s %-10s %-9s %-10s\n",$1,$2,$3,$8,$10}'
echo "raw table: $LOGDIR/sacct.psv"
