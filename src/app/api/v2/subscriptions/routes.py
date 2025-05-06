"""
V2 subscription routes that use optimized raw SQL queries for better performance.
"""
# Standard library imports
from datetime import datetime

# Third-party imports 
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, fields, reqparse

# Application imports
from app.api.v2.subscriptions import plan_ns, subscription_ns
from app.utils.json_helpers import convert_decimal_in_dict
from app.utils.sql_optimizations import (
    get_expiring_subscriptions,
    get_public_plans,
    get_subscription_history,
    get_subscription_stats,
    get_user_active_subscription,
)

# Models for documentation and request/response parsing
subscription_model = subscription_ns.model(
    "Subscription",
    {
        "id": fields.Integer(readonly=True),
        "user_id": fields.Integer(readonly=True),
        "plan_id": fields.Integer(),
        "status": fields.String(),
        "start_date": fields.DateTime(),
        "end_date": fields.DateTime(),
        "trial_end_date": fields.DateTime(),
        "canceled_at": fields.DateTime(),
        "current_period_start": fields.DateTime(),
        "current_period_end": fields.DateTime(),
        "payment_status": fields.String(),
        "quantity": fields.Integer(),
        "cancel_at_period_end": fields.Boolean(),
        "auto_renew": fields.Boolean(),
        "created_at": fields.DateTime(readonly=True),
        "updated_at": fields.DateTime(readonly=True),
    },
)

plan_model = plan_ns.model(
    "Plan",
    {
        "id": fields.Integer(readonly=True),
        "name": fields.String(),
        "description": fields.String(),
        "price": fields.Float(),
        "interval": fields.String(),
        "duration_months": fields.Integer(),
        "features": fields.String(),
        "status": fields.String(),
        "is_public": fields.Boolean(),
        "max_users": fields.Integer(),
        "parent_id": fields.Integer(),
        "sort_order": fields.Integer(),
        "created_at": fields.DateTime(readonly=True),
        "updated_at": fields.DateTime(readonly=True),
    },
)

subscription_stats_model = subscription_ns.model(
    "SubscriptionStats",
    {
        "active_count": fields.Integer(),
        "trial_count": fields.Integer(),
        "expiring_soon_count": fields.Integer(),
        "new_count": fields.Integer(),
        "recently_canceled_count": fields.Integer(),
    },
)

# Request parsers
subscription_history_parser = reqparse.RequestParser()
subscription_history_parser.add_argument(
    "status", type=str, help="Filter by status", location="args"
)
subscription_history_parser.add_argument(
    "from_date", type=str, help="Filter from date (YYYY-MM-DD)", location="args"
)
subscription_history_parser.add_argument(
    "to_date", type=str, help="Filter to date (YYYY-MM-DD)", location="args"
)
subscription_history_parser.add_argument(
    "page", type=int, default=1, help="Page number", location="args"
)
subscription_history_parser.add_argument(
    "per_page", type=int, default=10, help="Items per page", location="args"
)

plan_list_parser = reqparse.RequestParser()
plan_list_parser.add_argument(
    "status", type=str, help="Filter by status", location="args"
)
plan_list_parser.add_argument(
    "page", type=int, default=1, help="Page number", location="args"
)
plan_list_parser.add_argument(
    "per_page", type=int, default=10, help="Items per page", location="args"
)

expiring_parser = reqparse.RequestParser()
expiring_parser.add_argument(
    "days", type=int, default=7, help="Days to look ahead", location="args"
)


# Subscription routes
@subscription_ns.route("/active")
class ActiveSubscription(Resource):
    """Get the current user's active subscription"""

    @jwt_required()
    @subscription_ns.response(200, "Success")
    @subscription_ns.response(404, "No active subscription found")
    def get(self):
        """Get the current user's active subscription using optimized SQL"""
        current_user_id = get_jwt_identity()

        # Use the optimized SQL function
        subscription = get_user_active_subscription(current_user_id)

        if not subscription:
            subscription_ns.abort(404, "No active subscription found")

        # Convert Decimal to float
        subscription = convert_decimal_in_dict(subscription)
        return subscription


@subscription_ns.route("/history")
class SubscriptionHistory(Resource):
    """Get subscription history for the current user"""

    @jwt_required()
    @subscription_ns.expect(subscription_history_parser)
    @subscription_ns.response(200, "Success")
    def get(self):
        """Get the current user's subscription history using optimized SQL"""
        current_user_id = get_jwt_identity()
        args = subscription_history_parser.parse_args()

        # Process date parameters if provided
        from_date = None
        to_date = None

        if args.get("from_date"):
            try:
                from_date = datetime.fromisoformat(args["from_date"])
            except ValueError:
                subscription_ns.abort(400, "Invalid from_date format. Use YYYY-MM-DD")

        if args.get("to_date"):
            try:
                to_date = datetime.fromisoformat(args["to_date"])
            except ValueError:
                subscription_ns.abort(400, "Invalid to_date format. Use YYYY-MM-DD")

        # Use the optimized SQL function
        items, total, page, per_page, pages = get_subscription_history(
            current_user_id,
            status=args.get("status"),
            from_date=from_date,
            to_date=to_date,
            page=args.get("page", 1),
            per_page=args.get("per_page", 10),
        )

        # Convert Decimal to float
        items = convert_decimal_in_dict(items)

        # Return in the same format as v1 API for consistency
        return {
            "subscriptions": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }


@subscription_ns.route("/expiring")
class ExpiringSubscriptions(Resource):
    """Get subscriptions that are expiring soon (admin only)"""

    @jwt_required()
    @subscription_ns.expect(expiring_parser)
    @subscription_ns.response(200, "Success")
    @subscription_ns.response(403, "Forbidden - admin access required")
    def get(self):
        """Get subscriptions that are expiring soon using optimized SQL"""
        # This would typically check if the current user is an admin
        # For now, we'll use a placeholder - you would replace this with your actual admin check
        current_user_id = get_jwt_identity()

        # Placeholder for admin check - replace with your actual implementation
        is_admin = True  # Replace with actual admin check

        if not is_admin:
            subscription_ns.abort(403, "Admin access required")

        args = expiring_parser.parse_args()
        days = args.get("days", 7)

        # Use the optimized SQL function
        subscriptions = get_expiring_subscriptions(days)

        # Convert Decimal to float
        subscriptions = convert_decimal_in_dict(subscriptions)

        # Return in the same format as v1 API for consistency
        return {"subscriptions": subscriptions, "total": len(subscriptions)}


@subscription_ns.route("/stats")
class SubscriptionStats(Resource):
    """Get subscription statistics (admin only)"""

    @jwt_required()
    @subscription_ns.marshal_with(subscription_stats_model)
    @subscription_ns.response(200, "Success")
    @subscription_ns.response(403, "Forbidden - admin access required")
    def get(self):
        """Get subscription statistics using optimized SQL"""
        # This would typically check if the current user is an admin
        # For now, we'll use a placeholder - you would replace this with your actual admin check
        current_user_id = get_jwt_identity()

        # Placeholder for admin check - replace with your actual implementation
        is_admin = True  # Replace with actual admin check

        if not is_admin:
            subscription_ns.abort(403, "Admin access required")

        # Use the optimized SQL function
        stats = get_subscription_stats()

        return stats


# Plan routes
@plan_ns.route("/")
class PlanList(Resource):
    """List all public subscription plans"""

    @plan_ns.expect(plan_list_parser)
    @plan_ns.response(200, "Success")
    def get(self):
        """Get public subscription plans using optimized SQL"""
        args = plan_list_parser.parse_args()

        # Use the optimized SQL function
        items, total, page, per_page, pages = get_public_plans(
            status=args.get("status"),
            page=args.get("page", 1),
            per_page=args.get("per_page", 10),
        )

        # Convert Decimal to float
        items = convert_decimal_in_dict(items)

        # Return in the same format as v1 API for consistency
        return {
            "plans": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }
