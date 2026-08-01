"""Achievements ladder + avatar unlock/selection routes.

Pure logic lives in services/achievements.py; championship detection reuses
the champions computation (services/champions.py + the shared leaderboard
builder), so the "champion" avatar pack unlocks by the exact same rules that
crown the front page.
"""
import logging
import traceback

from flask import Blueprint, request
import sqlalchemy

from toms_gym.db import get_db_connection
from toms_gym.services import achievements
from toms_gym.services.champions import shape_champions

logger = logging.getLogger(__name__)

achievement_bp = Blueprint('achievement', __name__)


def _user_stats(session, user_id):
    row = session.execute(sqlalchemy.text("""
        SELECT COUNT(a.id) AS uploads,
               MAX((lr.report->>'total_in_plank_s')::float) AS best_hold,
               COUNT(*) FILTER (WHERE a.lift_type = 'Plank') AS plank_attempts
        FROM "Attempt" a
        JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
        LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id
        WHERE uc.user_id = :uid AND a.status <> 'failed'
    """), {"uid": user_id}).mappings().fetchone()
    return {"has_upload": (row["uploads"] or 0) > 0,
            "best_hold_s": row["best_hold"],
            "plank_attempts": row["plank_attempts"] or 0}


def _championship_count(session, user_id):
    from toms_gym.routes.competition_routes import _leaderboard_payload
    comps = session.execute(sqlalchemy.text(
        'SELECT id, name, end_date FROM "Competition" WHERE end_date < NOW()'
    )).mappings().fetchall()
    ended = [{"competition": {"id": str(c["id"]), "name": c["name"],
                              "end_date": str(c["end_date"])},
              "leaderboard": _leaderboard_payload(session, str(c["id"]))}
             for c in comps]
    return sum(1 for ch in shape_champions(ended) if ch["user_id"] == user_id)


def _earned_keys(session, user_id, stats):
    earned = achievements.evaluate(stats)
    if _championship_count(session, user_id) >= 1:
        earned.append("champion")
    return earned


@achievement_bp.route('/users/<string:user_id>/achievements')
def get_achievements(user_id):
    session = None
    try:
        session = get_db_connection()
        stats = _user_stats(session, user_id)
        earned = _earned_keys(session, user_id, stats)
        current = session.execute(
            sqlalchemy.text('SELECT avatar FROM "User" WHERE id = :uid'),
            {"uid": user_id}
        ).scalar()
        return {
            "ladder": achievements.LADDER,
            "earned": earned,
            "next": achievements.next_milestone(stats, earned),
            "avatar_keys": achievements.unlocked_avatar_keys(earned),
            "avatar": current,
        }
    except Exception as e:
        logger.error(f"Error fetching achievements: {str(e)}")
        logger.error(traceback.format_exc())
        if session:
            session.rollback()
        return {"error": f"Server error: {type(e).__name__}"}, 500
    finally:
        if session:
            session.close()


@achievement_bp.route('/users/<string:user_id>/avatar', methods=['PUT'])
def put_avatar(user_id):
    session = None
    try:
        key = (request.get_json(silent=True) or {}).get("key")
        session = get_db_connection()
        stats = _user_stats(session, user_id)
        earned = _earned_keys(session, user_id, stats)
        if key not in achievements.unlocked_avatar_keys(earned):
            return {"error": "avatar locked or unknown"}, 400
        session.execute(
            sqlalchemy.text('UPDATE "User" SET avatar = :k WHERE id = :uid'),
            {"k": key, "uid": user_id}
        )
        session.commit()
        return {"avatar": key, "avatar_url": achievements.resolve_avatar_url(key)}
    except Exception as e:
        logger.error(f"Error setting avatar: {str(e)}")
        logger.error(traceback.format_exc())
        if session:
            session.rollback()
        return {"error": f"Server error: {type(e).__name__}"}, 500
    finally:
        if session:
            session.close()
