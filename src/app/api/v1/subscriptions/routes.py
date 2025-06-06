"""
Routes for subscription plans and user subscriptions (V1 API).
"""
import json
from datetime import UTC, datetime, timedelta

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, fields

from app import db
from app.models.subscription_plan import (
    PlanStatus,
    SubscriptionInterval,
    SubscriptionPlan,
)
from app.models.user import User
from app.models.user_subscription import (
    PaymentStatus,
    SubscriptionStatus,
    UserSubscription,
)
from app.utils.auth import admin_required

from . import plan_ns, subscription_ns


def get_active_subscription_or_404(user_id):
    """
    Get the active subscription for a user or raise 404 error.
    
    Args:
        user_id (int): The ID of the user to check.
        
    Returns:
        UserSubscription: The active subscription for the user.
        
    Raises:
        werkzeug.exceptions.NotFound: If no active subscription is found.
    """
    return UserSubscription.query.filter_by(
        user_id=user_id,
        status=SubscriptionStatus.ACTIVE.value
    ).first_or_404('No active subscription found')


def find_active_subscription(user_id):
    """
    Find the active subscription for a user without raising an error if not found.
    
    Args:
        user_id (int): The ID of the user to check.
        
    Returns:
        UserSubscription or None: The active subscription for the user, or None if not found.
    """
    return UserSubscription.query.filter_by(
        user_id=user_id,
        status=SubscriptionStatus.ACTIVE.value
    ).first()


interval_model = plan_ns.model('SubscriptionInterval', {
    'value': fields.String(description='Interval value', enum=[i.value for i in SubscriptionInterval]),
    'name': fields.String(description='Interval display name'),
})

plan_status_model = plan_ns.model('PlanStatus', {
    'value': fields.String(description='Status value', enum=[s.value for s in PlanStatus]),
    'name': fields.String(description='Status display name'),
})

plan_model = plan_ns.model('SubscriptionPlan', {
    'id': fields.Integer(description='Plan ID'),
    'name': fields.String(required=True, description='Plan name'),
    'description': fields.String(required=True, description='Plan description'),
    'price': fields.Float(required=True, description='Plan price', attribute=lambda x: float(x.price) if hasattr(x, 'price') else None),
    'interval': fields.String(required=True, description='Billing interval', 
                              enum=[i.value for i in SubscriptionInterval]),
    'duration_months': fields.Integer(description='Duration in months', default=1),
    'features': fields.String(description='JSON string of features'),
    'status': fields.String(description='Plan status', 
                           enum=[s.value for s in PlanStatus], 
                           default=PlanStatus.ACTIVE.value),
    'is_public': fields.Boolean(description='Whether plan is publicly available', default=True),
    'max_users': fields.Integer(description='Maximum number of users allowed'),
    'parent_id': fields.Integer(description='Parent plan ID'),
    'sort_order': fields.Integer(description='Display order', default=0),
    'created_at': fields.DateTime(description='Creation date'),
    'updated_at': fields.DateTime(description='Last update date'),
})

plan_list_model = plan_ns.model('PlanList', {
    'plans': fields.List(fields.Nested(plan_model)),
    'total': fields.Integer(description='Total number of plans'),
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Items per page'),
    'pages': fields.Integer(description='Total number of pages')
})

plan_input_model = plan_ns.model('PlanInput', {
    'name': fields.String(required=True, description='Plan name'),
    'description': fields.String(required=True, description='Plan description'),
    'price': fields.Float(required=True, description='Plan price'),
    'interval': fields.String(required=True, description='Billing interval', 
                              enum=[i.value for i in SubscriptionInterval]),
    'duration_months': fields.Integer(description='Duration in months', default=1),
    'features': fields.Raw(description='Features as JSON object'),
    'status': fields.String(description='Plan status', 
                           enum=[s.value for s in PlanStatus], 
                           default=PlanStatus.ACTIVE.value),
    'is_public': fields.Boolean(description='Whether plan is publicly available', default=True),
    'max_users': fields.Integer(description='Maximum number of users allowed'),
    'parent_id': fields.Integer(description='Parent plan ID'),
    'sort_order': fields.Integer(description='Display order', default=0),
})

subscription_model = subscription_ns.model('UserSubscription', {
    'id': fields.Integer(description='Subscription ID'),
    'user_id': fields.Integer(description='User ID'),
    'plan_id': fields.Integer(description='Plan ID'),
    'status': fields.String(description='Subscription status', 
                           enum=[s.value for s in SubscriptionStatus]),
    'start_date': fields.DateTime(description='Start date'),
    'end_date': fields.DateTime(description='End date'),
    'trial_end_date': fields.DateTime(description='Trial end date'),
    'canceled_at': fields.DateTime(description='Cancellation date'),
    'current_period_start': fields.DateTime(description='Current period start'),
    'current_period_end': fields.DateTime(description='Current period end'),
    'payment_status': fields.String(description='Payment status'),
    'quantity': fields.Integer(description='Quantity'),
    'cancel_at_period_end': fields.Boolean(description='Cancel at period end'),
    'auto_renew': fields.Boolean(description='Auto renew'),
    'created_at': fields.DateTime(description='Creation date'),
    'updated_at': fields.DateTime(description='Last update date'),
})

subscription_with_plan_model = subscription_ns.model('UserSubscriptionWithPlan', {
    'id': fields.Integer(description='Subscription ID'),
    'user_id': fields.Integer(description='User ID'),
    'plan_id': fields.Integer(description='Plan ID'),
    'status': fields.String(description='Subscription status', 
                           enum=[s.value for s in SubscriptionStatus]),
    'start_date': fields.DateTime(description='Start date'),
    'end_date': fields.DateTime(description='End date'),
    'trial_end_date': fields.DateTime(description='Trial end date'),
    'canceled_at': fields.DateTime(description='Cancellation date'),
    'current_period_start': fields.DateTime(description='Current period start'),
    'current_period_end': fields.DateTime(description='Current period end'),
    'payment_status': fields.String(description='Payment status'),
    'quantity': fields.Integer(description='Quantity'),
    'cancel_at_period_end': fields.Boolean(description='Cancel at period end'),
    'auto_renew': fields.Boolean(description='Auto renew'),
    'created_at': fields.DateTime(description='Creation date'),
    'updated_at': fields.DateTime(description='Last update date'),
    'plan': fields.Nested(plan_model, description='Subscription plan details')
})

subscription_input_model = subscription_ns.model('SubscriptionInput', {
    'plan_id': fields.Integer(required=True, description='Plan ID to subscribe to'),
    'quantity': fields.Integer(description='Quantity (for seat-based plans)', default=1),
    'auto_renew': fields.Boolean(description='Whether to auto-renew the subscription', default=True),
    'trial_days': fields.Integer(description='Number of trial days (if applicable)', default=0)
})

plan_change_model = subscription_ns.model('PlanChangeInput', {
    'plan_id': fields.Integer(required=True, description='New plan ID to upgrade/downgrade to'),
    'prorate': fields.Boolean(description='Whether to prorate the subscription change', default=True)
})

cancel_subscription_model = subscription_ns.model('CancelSubscriptionInput', {
    'at_period_end': fields.Boolean(description='Whether to cancel at the end of the current period', default=True)
})

@plan_ns.route('/')
class SubscriptionPlanList(Resource):
    """Resource for listing and creating subscription plans"""
    
    @plan_ns.doc('list_plans', params={
        'page': {'type': 'integer', 'default': 1, 'description': 'Page number'},
        'per_page': {'type': 'integer', 'default': 10, 'description': 'Items per page'},
        'status': {'type': 'string', 'description': 'Filter by status (active, inactive, deprecated)'},
        'public_only': {'type': 'boolean', 'default': 'true', 'description': 'Show only public plans'}
    })
    @plan_ns.marshal_with(plan_list_model)
    def get(self):
        """List all subscription plans"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        public_only = request.args.get('public_only', 'true').lower() == 'true'
        
        query = SubscriptionPlan.query
        if status:
            query = query.filter(SubscriptionPlan.status == status)
        if public_only:
            query = query.filter(SubscriptionPlan.is_public == True)
            
        pagination = query.order_by(SubscriptionPlan.sort_order).paginate(
            page=page, per_page=per_page
        )
        
        return {
            'plans': pagination.items,
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages
        }
    
    @plan_ns.doc('create_plan')
    @plan_ns.expect(plan_input_model)
    @plan_ns.marshal_with(plan_model, code=201)
    @jwt_required()
    @admin_required()
    def post(self):
        """Create a new subscription plan (admin only)"""
        data = request.json
        features_dict = data.pop('features', None)
        features_json = json.dumps(features_dict) if features_dict else None
        
        plan = SubscriptionPlan(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            interval=data.get('interval', SubscriptionInterval.MONTHLY.value),
            duration_months=data.get('duration_months', 1),
            features=features_json,
            status=data.get('status', PlanStatus.ACTIVE.value),
            is_public=data.get('is_public', True),
            max_users=data.get('max_users'),
            parent_id=data.get('parent_id'),
            sort_order=data.get('sort_order', 0)
        )
        
        db.session.add(plan)
        db.session.commit()
        
        return plan, 201


@plan_ns.route('/<int:id>')
@plan_ns.param('id', 'The subscription plan identifier')
class SubscriptionPlanResource(Resource):
    """Resource for individual subscription plan operations"""
    
    @plan_ns.doc('get_plan')
    @plan_ns.marshal_with(plan_model)
    def get(self, id):
        """Get a specific subscription plan"""
        plan = SubscriptionPlan.query.get_or_404(id)
        return plan
    
    @plan_ns.doc('update_plan')
    @plan_ns.expect(plan_input_model)
    @plan_ns.marshal_with(plan_model)
    @jwt_required()
    @admin_required()
    def put(self, id):
        """Update a subscription plan (admin only)"""
        plan = SubscriptionPlan.query.get_or_404(id)
        data = request.json
        
        plan.name = data.get('name', plan.name)
        plan.description = data.get('description', plan.description)
        plan.price = data.get('price', plan.price)
        plan.interval = data.get('interval', plan.interval)
        plan.duration_months = data.get('duration_months', plan.duration_months)
        plan.status = data.get('status', plan.status)
        plan.is_public = data.get('is_public', plan.is_public)
        plan.max_users = data.get('max_users', plan.max_users)
        plan.parent_id = data.get('parent_id', plan.parent_id)
        plan.sort_order = data.get('sort_order', plan.sort_order)
        
        features_dict = data.get('features')
        if features_dict is not None:
            plan.features = json.dumps(features_dict)
        
        db.session.commit()
        return plan
    
    @plan_ns.doc('delete_plan')
    @plan_ns.response(204, 'Plan deleted')
    @jwt_required()
    @admin_required()
    def delete(self, id):
        """Delete a subscription plan (admin only)"""
        plan = SubscriptionPlan.query.get_or_404(id)
        db.session.delete(plan)
        db.session.commit()
        return '', 204


@plan_ns.route('/intervals')
class SubscriptionIntervals(Resource):
    """Resource for listing subscription intervals"""
    
    @plan_ns.doc('get_intervals')
    @plan_ns.marshal_list_with(interval_model)
    def get(self):
        """Get all available subscription intervals"""
        intervals = []
        for interval in SubscriptionInterval:
            intervals.append({
                'value': interval.value,
                'name': interval.name
            })
        return intervals


@plan_ns.route('/statuses')
class PlanStatuses(Resource):
    """Resource for listing plan statuses"""
    
    @plan_ns.doc('get_plan_statuses')
    @plan_ns.marshal_list_with(plan_status_model)
    def get(self):
        """Get all available plan statuses"""
        statuses = []
        for status in PlanStatus:
            statuses.append({
                'value': status.value,
                'name': status.name
            })
        return statuses


@subscription_ns.route('/')
class UserSubscriptionList(Resource):
    """Resource for creating subscriptions"""
    
    @subscription_ns.doc('create_subscription')
    @subscription_ns.expect(subscription_input_model)
    @subscription_ns.marshal_with(subscription_model, code=201)
    @subscription_ns.response(400, 'Invalid plan or user already has an active subscription')
    @subscription_ns.response(404, 'Plan not found')
    @jwt_required()
    def post(self):
        """Create a new subscription for the current user"""
        user_id = get_jwt_identity()
        data = request.json
        
        plan = SubscriptionPlan.query.get_or_404(data['plan_id'])
        if plan.status != PlanStatus.ACTIVE.value:
            return {'message': 'Cannot subscribe to inactive plan'}, 400
        
        active_subscription = find_active_subscription(user_id)
        
        if active_subscription:
            return {'message': 'User already has an active subscription'}, 400
        
        now = datetime.now(UTC)
        trial_days = data.get('trial_days', 0)
        
        trial_end_date = None
        if trial_days > 0:
            trial_end_date = now + timedelta(days=trial_days)
        
        # Calculate period end date based on the plan interval
        period_end = now + timedelta(days=30)  # Default to 30 days
        if plan.interval == SubscriptionInterval.ANNUAL.value:
            period_end = now + timedelta(days=365)
        elif plan.interval == SubscriptionInterval.SEMI_ANNUAL.value:
            period_end = now + timedelta(days=182)
        elif plan.interval == SubscriptionInterval.QUARTERLY.value:
            period_end = now + timedelta(days=90)
        elif plan.interval == SubscriptionInterval.MONTHLY.value:
            # Already set to 30 days
            pass
        
        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=now,
            trial_end_date=trial_end_date,
            current_period_start=now,
            current_period_end=period_end,
            payment_status=PaymentStatus.PAID.value if not trial_days else PaymentStatus.TRIAL.value,
            quantity=data.get('quantity', 1),
            auto_renew=data.get('auto_renew', True)
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return subscription, 201


@subscription_ns.route('/upgrade')
class SubscriptionUpgrade(Resource):
    """Resource for upgrading/downgrading subscriptions"""
    
    @subscription_ns.doc('upgrade_subscription')
    @subscription_ns.expect(plan_change_model)
    @subscription_ns.marshal_with(subscription_model)
    @subscription_ns.response(400, 'Invalid plan or no active subscription')
    @subscription_ns.response(404, 'Plan not found or no active subscription')
    @jwt_required()
    def post(self):
        """Upgrade or downgrade the current subscription"""
        user_id = get_jwt_identity()
        data = request.json
        
        subscription = get_active_subscription_or_404(user_id)
        
        new_plan = SubscriptionPlan.query.get_or_404(data['plan_id'])
        if new_plan.status != PlanStatus.ACTIVE.value:
            return {'message': 'Cannot upgrade to inactive plan'}, 400
        
        if subscription.plan_id == new_plan.id:
            return {'message': 'Already subscribed to this plan'}, 400
        
        # Handle the plan change
        prorate = data.get('prorate', True)
        
        # In a real system, we'd handle proration calculations here
        # For this example, we'll just update the subscription
        
        current_app.logger.info(
            f"Subscription change: User {user_id} changed from plan {subscription.plan_id} to {new_plan.id}"
        )
        
        subscription.plan_id = new_plan.id
        
        # If downgrading, we might keep the current period end
        # If upgrading and prorating, we might adjust the period end
        
        # For this example, we'll just update the plan ID
        db.session.commit()
        
        return subscription


@subscription_ns.route('/cancel')
class SubscriptionCancel(Resource):
    """Resource for canceling subscriptions"""
    
    @subscription_ns.doc('cancel_subscription')
    @subscription_ns.expect(cancel_subscription_model)
    @subscription_ns.marshal_with(subscription_model)
    @subscription_ns.response(404, 'No active subscription found')
    @jwt_required()
    def post(self):
        """Cancel the current subscription"""
        user_id = get_jwt_identity()
        data = request.json
        
        subscription = get_active_subscription_or_404(user_id)
        
        now = datetime.now(UTC)
        subscription.canceled_at = now
        
        # If canceling immediately, update status
        at_period_end = data.get('at_period_end', True)
        if not at_period_end:
            subscription.status = SubscriptionStatus.CANCELED.value
            subscription.end_date = now
        else:
            subscription.cancel_at_period_end = True
        
        db.session.commit()
        
        return subscription


@subscription_ns.route('/active')
class ActiveSubscription(Resource):
    """Resource for retrieving the active subscription"""
    
    @subscription_ns.doc('get_active_subscription')
    @subscription_ns.marshal_with(subscription_with_plan_model)
    @subscription_ns.response(404, 'No active subscription found')
    @jwt_required()
    def get(self):
        """Get the user's active subscription with plan details"""
        user_id = get_jwt_identity()
        
        subscription = get_active_subscription_or_404(user_id)
        
        return subscription


@subscription_ns.route('/history')
class SubscriptionHistory(Resource):
    """Resource for retrieving subscription history"""
    
    @subscription_ns.doc('get_subscription_history', params={
        'page': {'type': 'integer', 'default': 1, 'description': 'Page number'},
        'per_page': {'type': 'integer', 'default': 10, 'description': 'Items per page'},
        'status': {'type': 'string', 'description': 'Filter by status (comma-separated for multiple)'},
        'from_date': {'type': 'string', 'description': 'Filter subscriptions from this date (ISO format)'},
        'to_date': {'type': 'string', 'description': 'Filter subscriptions to this date (ISO format)'}
    })
    @subscription_ns.marshal_with(subscription_ns.model('SubscriptionHistoryList', {
        'subscriptions': fields.List(fields.Nested(subscription_with_plan_model)),
        'total': fields.Integer(description='Total number of subscriptions'),
        'page': fields.Integer(description='Current page number'),
        'per_page': fields.Integer(description='Items per page'),
        'pages': fields.Integer(description='Total number of pages')
    }))
    @jwt_required()
    def get(self):
        """Get user's subscription history with pagination and filtering"""
        user_id = get_jwt_identity()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        
        query = UserSubscription.query.filter_by(user_id=user_id)
        if status:
            statuses = status.split(',')
            query = query.filter(UserSubscription.status.in_(statuses))
        
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str)
                query = query.filter(UserSubscription.created_at >= from_date)
            except ValueError:
                pass  # Ignore invalid date format
        
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str)
                query = query.filter(UserSubscription.created_at <= to_date)
            except ValueError:
                pass  # Ignore invalid date format
        
        query = query.order_by(UserSubscription.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page)
        
        return {
            'subscriptions': pagination.items,
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages
        }


@subscription_ns.route('/indefinite')
class IndefiniteSubscription(Resource):
    """Resource for creating indefinite subscriptions (admin only)"""
    
    @subscription_ns.doc('create_indefinite_subscription')
    @subscription_ns.expect(subscription_input_model)
    @subscription_ns.marshal_with(subscription_model, code=201)
    @jwt_required()
    @admin_required()
    def post(self):
        """Create an indefinite subscription for a user (admin only)"""
        data = request.json
        if 'plan_id' not in data:
            return {'message': 'Plan ID is required'}, 400
        
        admin_id = get_jwt_identity()
        target_user_id = data.get('user_id')
        
        if not target_user_id:
            return {'message': 'User ID is required'}, 400
        
        plan = SubscriptionPlan.query.get_or_404(data['plan_id'])
        user = User.query.get_or_404(target_user_id)
        active_subscription = find_active_subscription(target_user_id)
        
        if active_subscription:
            return {'message': 'User already has an active subscription'}, 400
        
        now = datetime.now(UTC)
        subscription = UserSubscription(
            user_id=target_user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=now,
            trial_end_date=None,
            current_period_start=now,
            current_period_end=None,  # No period end for indefinite subscription
            payment_status=PaymentStatus.PAID.value,
            quantity=data.get('quantity', 1),
            auto_renew=True  # Always auto-renew for indefinite subscriptions
        )
        
        db.session.add(subscription)
        db.session.commit()
        current_app.logger.info(
            f"Indefinite subscription created: Admin {admin_id} created subscription for user {target_user_id} to plan {plan.id}"
        )
        
        return subscription, 201 