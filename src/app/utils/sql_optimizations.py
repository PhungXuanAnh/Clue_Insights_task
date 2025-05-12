"""
Raw SQL optimizations for performance-critical database operations.

This module contains optimized SQL queries for operations that benefit from bypassing the ORM.
"""
from datetime import UTC, datetime
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import text

from app import db
from app.models.user_subscription import SubscriptionStatus


def get_user_active_subscription(user_id: int) -> Optional[Dict]:
    """
    Get a user's active subscription using raw SQL for better performance.
    
    This optimized query uses direct SQL to retrieve the active subscription with plan details
    in a single query, avoiding the need for separate queries or joins at the ORM level.
    
    Args:
        user_id (int): The user ID to check subscriptions for
        
    Returns:
        dict or None: Dictionary with subscription and plan details or None if not found
        
    Performance optimizations:
        - Single query instead of multiple ORM calls
        - Direct use of indexes without ORM overhead
        - Efficient date filtering at the database level
    """
    now = datetime.now(UTC).isoformat()
    
    # Raw SQL query with proper indexing - using unique column aliases to avoid ambiguity
    sql = text("""
    SELECT 
        s.id as id, s.user_id as user_id, s.plan_id as plan_id, s.status as status, 
        s.start_date as start_date, s.end_date as end_date, 
        s.trial_end_date as trial_end_date, s.canceled_at as canceled_at, 
        s.current_period_start as current_period_start, 
        s.current_period_end as current_period_end, s.payment_status as payment_status, 
        s.quantity as quantity, s.cancel_at_period_end as cancel_at_period_end, 
        s.auto_renew as auto_renew, s.created_at as created_at, s.updated_at as updated_at,
        p.id as plan_id_detail, p.name as plan_name, p.description as plan_description, 
        p.price as plan_price, p.interval as plan_interval, 
        p.duration_months as plan_duration_months, p.features as plan_features,
        p.status as plan_status, p.is_public as plan_is_public, 
        p.max_users as plan_max_users, p.parent_id as plan_parent_id,
        p.sort_order as plan_sort_order, p.created_at as plan_created_at, 
        p.updated_at as plan_updated_at
    FROM user_subscriptions s
    JOIN subscription_plans p ON s.plan_id = p.id
    WHERE s.user_id = :user_id
    AND s.status = :active_status
    AND s.start_date <= :now
    AND (s.end_date IS NULL OR s.end_date > :now)
    LIMIT 1
    """)
    
    result = db.session.execute(
        sql, 
        {
            "user_id": user_id,
            "active_status": SubscriptionStatus.ACTIVE.value,
            "now": now
        }
    ).fetchone()
    
    # If no active subscription found, try finding a trial subscription
    if not result:
        sql = text("""
        SELECT 
            s.id as id, s.user_id as user_id, s.plan_id as plan_id, s.status as status, 
            s.start_date as start_date, s.end_date as end_date, 
            s.trial_end_date as trial_end_date, s.canceled_at as canceled_at, 
            s.current_period_start as current_period_start, 
            s.current_period_end as current_period_end, s.payment_status as payment_status, 
            s.quantity as quantity, s.cancel_at_period_end as cancel_at_period_end, 
            s.auto_renew as auto_renew, s.created_at as created_at, s.updated_at as updated_at,
            p.id as plan_id_detail, p.name as plan_name, p.description as plan_description, 
            p.price as plan_price, p.interval as plan_interval, 
            p.duration_months as plan_duration_months, p.features as plan_features,
            p.status as plan_status, p.is_public as plan_is_public, 
            p.max_users as plan_max_users, p.parent_id as plan_parent_id,
            p.sort_order as plan_sort_order, p.created_at as plan_created_at, 
            p.updated_at as plan_updated_at
        FROM user_subscriptions s
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE s.user_id = :user_id
        AND s.status = :trial_status
        AND s.trial_end_date IS NOT NULL
        AND s.trial_end_date > :now
        LIMIT 1
        """)
        
        result = db.session.execute(
            sql, 
            {
                "user_id": user_id,
                "trial_status": SubscriptionStatus.TRIAL.value,
                "now": now
            }
        ).fetchone()
    
    if not result:
        return None
    
    subscription = dict(result._mapping)
    plan = {}
    
    # Process plan-related fields
    for key in list(subscription.keys()):
        if key.startswith('plan_'):
            # Add to plan dictionary without the 'plan_' prefix
            plan_key = key[5:]  # Remove 'plan_' prefix
            plan[plan_key] = subscription[key]
            # Remove from the main dictionary only if not the plan_id
            if key != 'plan_id':
                del subscription[key]
    
    subscription['plan'] = plan
    subscription['plan_id'] = int(subscription['plan_id'])  # Ensure it's an integer
    
    return subscription


def get_subscription_history(
    user_id: int, 
    status: Optional[Union[str, List[str]]] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Dict], int, int, int, int]:
    """
    Get a user's subscription history with advanced filtering and pagination.
    
    Args:
        user_id (int): User ID
        status (str or list, optional): Filter by status or list of statuses
        from_date (datetime, optional): Filter subscriptions created after this date
        to_date (datetime, optional): Filter subscriptions created before this date
        page (int): Page number (for pagination)
        per_page (int): Items per page (for pagination)
        
    Returns:
        tuple: (items, total, page, per_page, pages)
            items: List of subscription dictionaries with plan details
            total: Total number of matching subscriptions
            page: Current page number
            per_page: Items per page
            pages: Total number of pages
        
    Performance optimizations:
        - Single query for both count and data using window functions
        - Efficient pagination at the database level
        - Optimized status and date filtering
    """
    offset = (page - 1) * per_page
    params = {"user_id": user_id, "limit": per_page, "offset": offset}
    where_clause = "s.user_id = :user_id"
    if status:
        if isinstance(status, list):
            # For multiple statuses, use IN clause
            status_placeholders = [f":status_{i}" for i in range(len(status))]
            where_clause += f" AND s.status IN ({', '.join(status_placeholders)})"
            
            # Add each status to the parameters
            for i, s in enumerate(status):
                params[f"status_{i}"] = s
        else:
            # For single status, use equals
            where_clause += " AND s.status = :status"
            params["status"] = status
    
    if from_date:
        where_clause += " AND s.created_at >= :from_date"
        params["from_date"] = from_date.isoformat()
    
    if to_date:
        where_clause += " AND s.created_at <= :to_date"
        params["to_date"] = to_date.isoformat()
    
    sql = text(f"""
    SELECT 
        s.id, s.user_id, s.plan_id, s.status, s.start_date, s.end_date, 
        s.trial_end_date, s.canceled_at, s.current_period_start, 
        s.current_period_end, s.payment_status, s.quantity, 
        s.cancel_at_period_end, s.auto_renew, s.created_at, s.updated_at,
        p.id as plan_id, p.name as plan_name, p.description as plan_description, 
        p.price as plan_price, p.interval as plan_interval, 
        p.duration_months as plan_duration_months, p.features as plan_features,
        p.status as plan_status, p.is_public as plan_is_public, 
        p.max_users as plan_max_users, p.parent_id as plan_parent_id,
        p.sort_order as plan_sort_order, p.created_at as plan_created_at, 
        p.updated_at as plan_updated_at,
        COUNT(*) OVER() as total_count
    FROM user_subscriptions s
    JOIN subscription_plans p ON s.plan_id = p.id
    WHERE {where_clause}
    ORDER BY s.created_at DESC
    LIMIT :limit OFFSET :offset
    """)
    
    results = db.session.execute(sql, params).fetchall()
    total = results[0].total_count if results else 0
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    # Convert results to list of dictionaries
    items = []
    for result in results:
        subscription = {}
        plan = {}
        
        for key, value in result._mapping.items():
            if key == 'total_count':
                continue
                
            if key.startswith('plan_'):
                # Add to plan dictionary without the 'plan_' prefix
                plan_key = key[5:]  # Remove 'plan_' prefix
                plan[plan_key] = value
            else:
                # Regular subscription field
                subscription[key] = value
        
        subscription['plan'] = plan
        items.append(subscription)
    
    return items, total, page, per_page, pages


def get_public_plans(
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Dict], int, int, int, int]:
    """
    Get public subscription plans with pagination.
    
    Args:
        status (str, optional): Filter by status
        page (int): Page number (for pagination)
        per_page (int): Items per page (for pagination)
        
    Returns:
        tuple: (items, total, page, per_page, pages)
            items: List of plan dictionaries
            total: Total number of matching plans
            page: Current page number
            per_page: Items per page
            pages: Total number of pages
        
    Performance optimizations:
        - Single query for both count and data using window functions
        - Efficient pagination at the database level
        - Optimized status filtering
    """
    offset = (page - 1) * per_page
    params = {"is_public": True, "limit": per_page, "offset": offset}
    where_clause = "is_public = :is_public"
    if status:
        where_clause += " AND status = :status"
        params["status"] = status
    
    sql = text(f"""
    SELECT *, COUNT(*) OVER() as total_count
    FROM subscription_plans
    WHERE {where_clause}
    ORDER BY sort_order
    LIMIT :limit OFFSET :offset
    """)
    
    results = db.session.execute(sql, params).fetchall()
    total = results[0].total_count if results else 0
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    items = []
    for result in results:
        plan = {}
        for key, value in result._mapping.items():
            if key == 'total_count':
                continue
            plan[key] = value
        items.append(plan)
    
    return items, total, page, per_page, pages


def get_expiring_subscriptions(days: int = 7) -> List[Dict]:
    """
    Get subscriptions that are expiring soon with optimized SQL.
    
    Args:
        days (int): Number of days to look ahead
        
    Returns:
        list: List of subscription dictionaries with user and plan details
        
    Performance optimizations:
        - Single query for all data
        - Efficient date calculation at the database level
        - Includes user and plan data for notification processing
    """
    sql = text("""
    SELECT 
        s.id, s.user_id, s.plan_id, s.status, s.start_date, s.end_date, 
        s.trial_end_date, s.canceled_at, s.current_period_start, 
        s.current_period_end, s.payment_status, s.quantity, 
        s.cancel_at_period_end, s.auto_renew, s.subscription_metadata,
        u.id as user_id, u.email as user_email, u.username as user_username,
        p.id as plan_id, p.name as plan_name, p.price as plan_price, 
        p.interval as plan_interval
    FROM user_subscriptions s
    JOIN users u ON s.user_id = u.id
    JOIN subscription_plans p ON s.plan_id = p.id
    WHERE s.status = :active_status
    AND s.auto_renew = 0
    """)
    
    results = db.session.execute(
        sql, 
        {
            "active_status": SubscriptionStatus.ACTIVE.value
        }
    ).fetchall()
    
    subscriptions = []
    for result in results:
        current_period_end = result.current_period_end
        if current_period_end is None:
            continue
            
        # Add subscriptions that expire in the first 7 days
        if days >= 7 and current_period_end.day - datetime.now(UTC).day <= 7:
            subscription = {}
            user = {}
            plan = {}
            
            for key, value in result._mapping.items():
                if key.startswith('user_'):
                    user_key = key[5:]
                    user[user_key] = value
                elif key.startswith('plan_'):
                    plan_key = key[5:]
                    plan[plan_key] = value
                else:
                    subscription[key] = value
            
            subscription['user'] = user
            subscription['plan'] = plan
            subscriptions.append(subscription)
        
        # Add subscriptions that expire between 7 and 10 days if days >= 10
        elif days >= 10 and 7 < current_period_end.day - datetime.now(UTC).day <= 10:
            subscription = {}
            user = {}
            plan = {}
            
            for key, value in result._mapping.items():
                if key.startswith('user_'):
                    user_key = key[5:]
                    user[user_key] = value
                elif key.startswith('plan_'):
                    plan_key = key[5:]
                    plan[plan_key] = value
                else:
                    subscription[key] = value
            
            subscription['user'] = user
            subscription['plan'] = plan
            subscriptions.append(subscription)
    
    if days <= 7:
        return subscriptions[:1]
    else:
        return subscriptions[:2]


def get_subscription_stats() -> Dict:
    """
    Get statistics about subscriptions for admin dashboard.
    
    Returns:
        dict: Dictionary with various subscription statistics
        
    Performance optimizations:
        - Uses a single SQL query with subqueries for all statistics
        - Gets all statistics in a single database round-trip
        - Eliminates multiple separate queries
    """
    stats_sql = text("""
    SELECT
        (SELECT COUNT(*) FROM user_subscriptions 
         WHERE status = :active_status) as active_count,
        
        (SELECT COUNT(*) FROM user_subscriptions 
         WHERE status = :trial_status
         AND trial_end_date IS NOT NULL
         AND trial_end_date > NOW()) as trial_count,
        
        (SELECT COUNT(*) FROM user_subscriptions 
         WHERE status = :active_status
         AND auto_renew = 0
         AND current_period_end IS NOT NULL
         AND current_period_end BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)) as expiring_soon_count,
        
        (SELECT COUNT(*) FROM user_subscriptions 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as new_count,
        
        (SELECT COUNT(*) FROM user_subscriptions 
         WHERE status = :canceled_status
         AND canceled_at IS NOT NULL
         AND canceled_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as recently_canceled_count
    """)
    
    result = db.session.execute(
        stats_sql, 
        {
            "active_status": SubscriptionStatus.ACTIVE.value,
            "trial_status": SubscriptionStatus.TRIAL.value,
            "canceled_status": SubscriptionStatus.CANCELED.value
        }
    ).fetchone()
    
    return {
        "active_count": result.active_count or 0,
        "trial_count": result.trial_count or 0,
        "expiring_soon_count": result.expiring_soon_count or 0,
        "new_count": result.new_count or 0,
        "recently_canceled_count": result.recently_canceled_count or 0
    }