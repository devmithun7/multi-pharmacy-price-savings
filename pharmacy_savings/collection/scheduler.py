"""
Simple scheduler for periodic price collection.

Run with:  python -m pharmacy_savings.collection.scheduler
Or use cron / Windows Task Scheduler for automated execution.
"""
import time

import schedule

from .pipeline import run_collection


def schedule_daily_collection(hour=9, minute=0):
    """Schedule daily collection at the specified time (default 9:00 AM)."""
    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(run_collection)
    print(f"Scheduled daily price collection at {hour:02d}:{minute:02d}")
    print("Scheduler running... (Press Ctrl+C to stop)\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


def schedule_interval_collection(interval_hours=6):
    """Schedule collection at regular intervals (default every 6 hours)."""
    schedule.every(interval_hours).hours.do(run_collection)
    print(f"Scheduled price collection every {interval_hours} hours")
    print("Scheduler running... (Press Ctrl+C to stop)\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


if __name__ == "__main__":
    # Option 1: Daily collection at 9:00 AM
    schedule_daily_collection(hour=9, minute=0)

    # Option 2: Collection every 6 hours
    # schedule_interval_collection(interval_hours=6)
