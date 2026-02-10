from flask import Blueprint, request, jsonify
import sqlalchemy
from toms_gym.db import get_db_connection
import datetime
import logging

weekly_lifts_bp = Blueprint('weekly_lifts', __name__)
logger = logging.getLogger(__name__)

VALID_LIFT_TYPES = ['bench', 'squat', 'deadlift', 'sitting_press']


def get_monday_of_week(date):
    """Return the Monday of the week for a given date."""
    days_since_monday = date.weekday()
    return date - datetime.timedelta(days=days_since_monday)


@weekly_lifts_bp.route('/users/<string:user_id>/weekly-lifts', methods=['GET'])
def get_weekly_lifts(user_id):
    """
    Get all weekly lifts for a user, optionally limited by number of weeks.
    Query params:
        - weeks: number of weeks to return (default: all)
    """
    try:
        weeks_param = request.args.get('weeks', type=int)

        session = get_db_connection()

        # Build query
        query = """
            SELECT id, week_start_date, lift_type, weight_lbs, created_at, updated_at
            FROM "WeeklyMaxLift"
            WHERE user_id = :user_id
            ORDER BY week_start_date DESC, lift_type
        """

        results = session.execute(
            sqlalchemy.text(query),
            {"user_id": user_id}
        ).fetchall()
        session.close()

        # Group by week
        weeks_dict = {}
        for row in results:
            week_date = row[1]  # week_start_date
            week_key = week_date.isoformat()

            if week_key not in weeks_dict:
                # Format label like "Week 1 (1/12)"
                weeks_dict[week_key] = {
                    "week_start_date": week_key,
                    "label": f"{week_date.month}/{week_date.day}",
                    "lifts": {},
                    "lift_ids": {}
                }

            lift_type = row[2]  # lift_type
            weight = float(row[3])  # weight_lbs
            lift_id = str(row[0])  # id

            weeks_dict[week_key]["lifts"][lift_type] = weight
            weeks_dict[week_key]["lift_ids"][lift_type] = lift_id

        # Convert to list and calculate totals
        weeks_list = []
        for week_key in sorted(weeks_dict.keys(), reverse=True):
            week_data = weeks_dict[week_key]
            total = sum(week_data["lifts"].values())
            week_data["total"] = total
            weeks_list.append(week_data)

        # Apply weeks limit if specified
        if weeks_param and weeks_param > 0:
            weeks_list = weeks_list[:weeks_param]

        return jsonify({"weeks": weeks_list})

    except Exception as e:
        logger.error(f"Error in get_weekly_lifts: {str(e)}")
        return jsonify({"error": str(e)}), 500


@weekly_lifts_bp.route('/users/<string:user_id>/weekly-lifts', methods=['POST'])
def create_or_update_weekly_lift(user_id):
    """
    Create or update a weekly lift entry.
    Request body:
        - week_start_date: date string (YYYY-MM-DD), will be normalized to Monday
        - lift_type: one of 'bench', 'squat', 'deadlift', 'sitting_press'
        - weight_lbs: decimal number
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        week_start_date = data.get('week_start_date')
        lift_type = data.get('lift_type')
        weight_lbs = data.get('weight_lbs')

        if not week_start_date:
            return jsonify({"error": "week_start_date is required"}), 400
        if not lift_type:
            return jsonify({"error": "lift_type is required"}), 400
        if weight_lbs is None:
            return jsonify({"error": "weight_lbs is required"}), 400

        # Validate lift type
        if lift_type not in VALID_LIFT_TYPES:
            return jsonify({"error": f"Invalid lift_type. Must be one of: {VALID_LIFT_TYPES}"}), 400

        # Parse and normalize date to Monday
        try:
            parsed_date = datetime.date.fromisoformat(week_start_date)
            monday_date = get_monday_of_week(parsed_date)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Validate weight
        try:
            weight_lbs = float(weight_lbs)
            if weight_lbs < 0:
                return jsonify({"error": "weight_lbs must be non-negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "weight_lbs must be a number"}), 400

        session = get_db_connection()

        # Use upsert (INSERT ... ON CONFLICT UPDATE)
        query = """
            INSERT INTO "WeeklyMaxLift" (user_id, week_start_date, lift_type, weight_lbs)
            VALUES (:user_id, :week_start_date, :lift_type, :weight_lbs)
            ON CONFLICT (user_id, week_start_date, lift_type)
            DO UPDATE SET weight_lbs = :weight_lbs, updated_at = CURRENT_TIMESTAMP
            RETURNING id, week_start_date, lift_type, weight_lbs, created_at, updated_at
        """

        result = session.execute(
            sqlalchemy.text(query),
            {
                "user_id": user_id,
                "week_start_date": monday_date,
                "lift_type": lift_type,
                "weight_lbs": weight_lbs
            }
        ).fetchone()
        session.commit()
        session.close()

        return jsonify({
            "id": str(result[0]),
            "week_start_date": result[1].isoformat(),
            "lift_type": result[2],
            "weight_lbs": float(result[3]),
            "created_at": result[4].isoformat() if result[4] else None,
            "updated_at": result[5].isoformat() if result[5] else None
        }), 201

    except Exception as e:
        logger.error(f"Error in create_or_update_weekly_lift: {str(e)}")
        return jsonify({"error": str(e)}), 500


@weekly_lifts_bp.route('/users/<string:user_id>/weekly-lifts/<string:lift_id>', methods=['DELETE'])
def delete_weekly_lift(user_id, lift_id):
    """
    Delete a specific weekly lift entry.
    """
    try:
        session = get_db_connection()

        # Verify the lift belongs to the user before deleting
        result = session.execute(
            sqlalchemy.text("""
                DELETE FROM "WeeklyMaxLift"
                WHERE id = :lift_id AND user_id = :user_id
                RETURNING id
            """),
            {"lift_id": lift_id, "user_id": user_id}
        ).fetchone()
        session.commit()
        session.close()

        if not result:
            return jsonify({"error": "Lift entry not found or does not belong to user"}), 404

        return jsonify({"message": "Lift entry deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error in delete_weekly_lift: {str(e)}")
        return jsonify({"error": str(e)}), 500
