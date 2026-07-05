"""Debug test for generate_next_week — print full traceback."""
import sys, os, json, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["DATABASE_URL"] = "sqlite:///fitness.db"

from app.database import SessionLocal
from app.models.orm_models import Week, Mesocycle, Day, ExerciseSlot, UserCurrentState
from app.engine.generator import generate_next_week

async def main():
    db = SessionLocal()
    event_queue = asyncio.Queue()

    # Print current DB state
    weeks = db.query(Week).order_by(Week.id.desc()).all()
    print(f"\n=== DB State: {len(weeks)} weeks ===")
    for w in weeks:
        days = db.query(Day).filter(Day.week_id == w.id).all()
        slots_count = sum(
            db.query(ExerciseSlot).filter(ExerciseSlot.day_id == d.id).count()
            for d in days
        )
        print(f"  Week #{w.week_number} (id={w.id}, mesocycle_id={w.mesocycle_id}, status={w.status}): {len(days)} days, {slots_count} slots")

    ucs = db.query(UserCurrentState).first()
    print(f"\nUCS: pool_loaded={ucs.pool_loaded if ucs else 'N/A'}")

    # Find active week
    current_week = db.query(Week).filter(Week.status == "active").order_by(Week.id.desc()).first()
    if not current_week:
        print("No active week found!")
        return

    print(f"\nGenerating next week after week #{current_week.week_number} (id={current_week.id})...")

    # Consume SSE events in background
    async def consume_queue():
        while True:
            event_type, data = await event_queue.get()
            if event_type == "__END__":
                break
            print(f"  [SSE] {event_type}: {json.dumps(data, ensure_ascii=False)[:120] if isinstance(data, dict) else data}")

    consumer_task = asyncio.create_task(consume_queue())

    try:
        new_week = await generate_next_week(current_week, db, event_queue)
        print(f"\n✅ Result: week #{new_week.week_number if new_week else 'None'}")
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()

    await event_queue.put(("__END__", None))
    await consumer_task
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
