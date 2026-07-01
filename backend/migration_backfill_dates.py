"""迁移脚本：为现有 Week 和 Day 记录回填 start_date / date 字段。

运行方式：
  cd backend && python migration_backfill_dates.py

逻辑：
  1. Week.start_date ← Week.generated_at 所在周的周一
  2. Day.date ← Week.start_date + (Day.day_of_week - 1)
  3. 如 Day.day_of_week 为 0，用 Day.day_order 推算（第N个训练日→适合的 day_of_week）
"""

import sys
from datetime import datetime, timedelta


def get_monday(dt: datetime) -> str:
    """返回 dt 所在周的周一的 YYYY-MM-DD。"""
    monday = dt - timedelta(days=dt.weekday())  # weekday(): Mon=0
    return monday.strftime("%Y-%m-%d")


def main():
    # 延迟导入，避免在无数据库环境报错
    from app.database import SessionLocal
    from app.models.orm_models import Week, Day, Macrocycle
    from sqlalchemy import text

    db = SessionLocal()

    try:
        # ── 1. 回填 Week.start_date ──────────────────────────
        weeks = db.query(Week).all()
        week_fixed = 0
        for w in weeks:
            if w.start_date:
                continue  # 已有值则跳过
            if w.generated_at:
                w.start_date = get_monday(w.generated_at)
            else:
                # 没有 generated_at 的兜底：用 id 倒推
                w.start_date = "2026-06-01"
            week_fixed += 1
            print(f"  Week id={w.id} → start_date={w.start_date}")

        # ── 2. 确保 Macrocycle.start_date 非空 ───────────────
        macrocycles = db.query(Macrocycle).all()
        mc_fixed = 0
        for mc in macrocycles:
            if not mc.start_date:
                # 从第一个 Week 的 start_date 倒推
                first_week = db.query(Week).join(
                    Macrocycle, Week.mesocycle_id == Macrocycle.id
                ).filter(
                    Macrocycle.id == mc.id
                ).order_by(Week.id.asc()).first()
                if first_week and first_week.start_date:
                    mc.start_date = first_week.start_date
                else:
                    mc.start_date = "2026-06-01"
                mc_fixed += 1
                print(f"  Macrocycle id={mc.id} → start_date={mc.start_date}")

        # ── 3. 回填 Day.date ─────────────────────────────────
        days = db.query(Day).all()
        day_fixed = 0
        for d in days:
            if d.date:
                continue  # 已有值则跳过

            # 获取关联的 Week 的 start_date
            week = db.query(Week).filter(Week.id == d.week_id).first()
            if not week or not week.start_date:
                print(f"  ⚠️ Day id={d.id}: 关联 Week 无 start_date，跳过")
                continue

            # 用 day_of_week 推算日期
            dow = d.day_of_week or 0
            if dow < 1 or dow > 7:
                # 兜底：用 day_order 推算
                dow = d.day_order * 2 - 1  # 第1天→周一(1), 第2天→周三(3), ...
                if dow > 7:
                    dow = d.day_order

            week_start = datetime.strptime(week.start_date, "%Y-%m-%d")
            day_date = week_start + timedelta(days=dow - 1)
            d.date = day_date.strftime("%Y-%m-%d")
            day_fixed += 1
            print(f"  Day id={d.id} (week={d.week_id}, dow={dow}) → date={d.date}")

        # ── 提交 ─────────────────────────────────────────────
        db.commit()
        print(f"\n✅ 迁移完成！")
        print(f"   回填 Week: {week_fixed} 条")
        print(f"   回填 Macrocycle: {mc_fixed} 条")
        print(f"   回填 Day: {day_fixed} 条")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
