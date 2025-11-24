#!/bin/bash
# Monitor large-scale validation progress

JOB_ID=333504
WORK_DIR="validation_1000_run"
TOTAL=949

echo "=========================================="
echo "DPAM v2.0 Large-Scale Validation Monitor"
echo "=========================================="
echo ""

# SLURM job status
echo "SLURM Job Status (Job ID: $JOB_ID):"
RUNNING=$(squeue -j $JOB_ID -h | grep ' R ' | wc -l)
PENDING=$(squeue -j $JOB_ID -h | grep ' PD' | wc -l)
TOTAL_QUEUED=$((RUNNING + PENDING))

echo "  Running:  $RUNNING/100 concurrent jobs"
echo "  Pending:  $PENDING jobs"
echo "  Total in queue: $TOTAL_QUEUED/$TOTAL"
echo ""

# Completed jobs (have state files)
COMPLETED=$(ls $WORK_DIR/*.dpam_state.json 2>/dev/null | wc -l)
PERCENT_COMPLETE=$(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc)

echo "Pipeline Completion:"
echo "  Completed: $COMPLETED/$TOTAL ($PERCENT_COMPLETE%)"
echo ""

# Success/failure counts
if [ $COMPLETED -gt 0 ]; then
    SUCCESS=$(grep -l "\"completed_steps\":" $WORK_DIR/.*.dpam_state.json 2>/dev/null | xargs grep -l "24" | wc -l)
    FAILED=$(grep "\"failed_steps\"" $WORK_DIR/.*.dpam_state.json 2>/dev/null | grep -v "\"failed_steps\": \[\]" | wc -l)
    IN_PROGRESS=$((COMPLETED - SUCCESS - FAILED))

    echo "Detailed Status:"
    echo "  Success (24/24 steps): $SUCCESS"
    echo "  In progress:           $IN_PROGRESS"
    echo "  Failed:                $FAILED"
    echo ""
fi

# Output files check
FINAL_DOMAINS=$(ls $WORK_DIR/*.finalDPAM.domains 2>/dev/null | wc -l)
PREDICTIONS=$(ls $WORK_DIR/*.step23_predictions 2>/dev/null | wc -l)

echo "Output Files:"
echo "  Final domains:  $FINAL_DOMAINS"
echo "  Predictions:    $PREDICTIONS"
echo ""

# Error summary
ERROR_COUNT=$(grep -i "error" $WORK_DIR/slurm_logs/*.err 2>/dev/null | wc -l)
echo "Errors in logs: $ERROR_COUNT"
echo ""

# Estimated completion time
if [ $RUNNING -gt 0 ] && [ $COMPLETED -gt 0 ]; then
    # Calculate average time per job so far
    # This is rough - assumes linear progress
    REMAINING=$((TOTAL - COMPLETED))
    JOBS_IN_PARALLEL=100
    EST_BATCHES=$(echo "scale=0; ($REMAINING + $JOBS_IN_PARALLEL - 1) / $JOBS_IN_PARALLEL" | bc)
    EST_MINUTES=$((EST_BATCHES * 5))  # Assume 5 min per batch

    echo "Estimated time remaining: ~$EST_MINUTES minutes"
    echo ""
fi

# Recent activity
echo "Recent log activity (last 5 lines from task 0):"
tail -5 $WORK_DIR/slurm_logs/${JOB_ID}_0.out 2>/dev/null || echo "  (No log yet)"
echo ""

echo "=========================================="
echo "Use: watch -n 30 bash scripts/monitor_validation.sh"
echo "Or:  tail -f $WORK_DIR/slurm_logs/${JOB_ID}_0.out"
echo "=========================================="
