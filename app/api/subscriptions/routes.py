"""
Routes for subscription plans and user subscriptions.
"""
import json
from datetime import datetime, timedelta
from http import HTTPStatus

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
from app.models.user_subscription import PaymentStatus, SubscriptionStatus, UserSubscription
from app.utils.auth import admin_required

from . import plan_ns, subscription_ns

# Define the subscription interval enum model
interval_model = plan_ns.model('SubscriptionInterval', {
    'value': fields.String(description='Interval value', enum=[i.value for i in SubscriptionInterval]),
    'name': fields.String(description='Interval display name'),
})

# Define the plan status enum model
plan_status_model = plan_ns.model('PlanStatus', {
    'value': fields.String(description='Status value', enum=[s.value for s in PlanStatus]),
    'name': fields.String(description='Status display name'),
})

# Define the subscription plan model for API
plan_model = plan_ns.model('SubscriptionPlan', {
    'id': fields.Integer(description='Plan ID'),
    'name': fields.String(required=True, description='Plan name'),
    'description': fields.String(required=True, description='Plan description'),
    'price': fields.Float(required=True, description='Plan price'),
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

# Define the plan list response model
plan_list_model = plan_ns.model('PlanList', {
    'plans': fields.List(fields.Nested(plan_model)),
    'total': fields.Integer(description='Total number of plans'),
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Items per page'),
    'pages': fields.Integer(description='Total number of pages')
})

# Input model for creating/updating plans
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

# Define the user subscription model for API
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

# Input model for creating a subscription
subscription_input_model = subscription_ns.model('SubscriptionInput', {
    'plan_id': fields.Integer(required=True, description='Plan ID to subscribe to'),
    'quantity': fields.Integer(description='Quantity (for seat-based plans)', default=1),
    'auto_renew': fields.Boolean(description='Whether to auto-renew the subscription', default=True),
    'trial_days': fields.Integer(description='Number of trial days (if applicable)', default=0)
})

# Define input model for upgrading/downgrading subscription
plan_change_model = subscription_ns.model('PlanChangeInput', {
    'plan_id': fields.Integer(required=True, description='New plan ID to upgrade/downgrade to'),
    'prorate': fields.Boolean(description='Whether to prorate the subscription change', default=True)
})

# API routes for subscription plans
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
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        public_only = request.args.get('public_only', 'true').lower() == 'true'
        
        # Build the query
        query = SubscriptionPlan.query
        
        # Apply filters
        if status:
            query = query.filter(SubscriptionPlan.status == status)
        if public_only:
            query = query.filter(SubscriptionPlan.is_public == True)
            
        # Get paginated results
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
        
        # Handle features as dict
        features_dict = data.pop('features', None)
        features_json = json.dumps(features_dict) if features_dict else None
        
        # Create the new plan
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
        
        # Update basic fields
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
        
        # Handle features separately
        if 'features' in data:
            plan.set_features_dict(data['features'])
        
        db.session.commit()
        return plan
    
    @plan_ns.doc('delete_plan')
    @plan_ns.response(204, 'Plan deleted')
    @jwt_required()
    @admin_required()
    def delete(self, id):
        """Delete a subscription plan (admin only)"""
        plan = SubscriptionPlan.query.get_or_404(id)
        
        # Check if plan has active subscriptions
        active_subs = UserSubscription.query.filter_by(
            plan_id=id, 
            status=SubscriptionStatus.ACTIVE.value
        ).first()
        
        if active_subs:
            plan_ns.abort(400, f"Cannot delete plan with active subscriptions. Deactivate it instead.")
        
        db.session.delete(plan)
        db.session.commit()
        return '', 204


@plan_ns.route('/intervals')
class SubscriptionIntervals(Resource):
    """Resource for subscription interval options"""
    
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
    """Resource for plan status options"""
    
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


# API routes for user subscriptions
@subscription_ns.route('/')
class UserSubscriptionList(Resource):
    """Resource for user subscription operations"""
    
    @subscription_ns.doc('create_subscription')
    @subscription_ns.expect(subscription_input_model)
    @subscription_ns.marshal_with(subscription_model, code=201)
    @subscription_ns.response(400, 'Invalid plan or user already has an active subscription')
    @subscription_ns.response(404, 'Plan not found')
    @jwt_required()
    def post(self):
        """Subscribe to a plan"""
        user_id = get_jwt_identity()
        data = request.json
        
        # Check if plan exists and is active
        plan = SubscriptionPlan.query.get_or_404(data['plan_id'])
        if plan.status != PlanStatus.ACTIVE.value:
            subscription_ns.abort(400, f"Cannot subscribe to an inactive plan")
        
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Check if user already has an active subscription
        existing_subscription = UserSubscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE.value
        ).first()
        
        if existing_subscription:
            subscription_ns.abort(400, f"User already has an active subscription. Please cancel or upgrade it instead.")
        
        # Calculate subscription dates
        now = datetime.utcnow()
        start_date = now
        current_period_start = now
        
        # Calculate end date based on plan duration
        if plan.duration_months:
            # Add months to current date
            month = now.month - 1 + plan.duration_months
            year = now.year + month // 12
            month = month % 12 + 1
            end_date = datetime(year, month, min(now.day, 28), now.hour, now.minute, now.second)
            current_period_end = end_date
        else:
            # Indefinite subscription
            end_date = None
            current_period_end = None
        
        # Handle trial period if specified
        trial_days = data.get('trial_days', 0)
        trial_end_date = None
        status = SubscriptionStatus.ACTIVE.value
        
        if trial_days > 0:
            trial_end_date = now + timedelta(days=trial_days)
            status = SubscriptionStatus.TRIAL.value
        
        # Create the subscription
        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            trial_end_date=trial_end_date,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            payment_status=PaymentStatus.PAID.value,  # Assuming payment is handled elsewhere
            quantity=data.get('quantity', 1),
            auto_renew=data.get('auto_renew', True)
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return subscription, 201

# API route for upgrading/downgrading a subscription
@subscription_ns.route('/upgrade')
class SubscriptionUpgrade(Resource):
    """Resource for upgrading/downgrading user subscription"""
    
    @subscription_ns.doc('upgrade_subscription')
    @subscription_ns.expect(plan_change_model)
    @subscription_ns.marshal_with(subscription_model)
    @subscription_ns.response(400, 'Invalid plan or no active subscription')
    @subscription_ns.response(404, 'Plan not found or no active subscription')
    @jwt_required()
    def post(self):
        """Upgrade or downgrade to a different subscription plan"""
        user_id = get_jwt_identity()
        data = request.json
        
        # Get target plan
        new_plan = SubscriptionPlan.query.get_or_404(data['plan_id'])
        if new_plan.status != PlanStatus.ACTIVE.value:
            subscription_ns.abort(400, f"Cannot upgrade to an inactive plan")
        
        # Get current active subscription
        subscription = UserSubscription.query.filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        if not subscription:
            subscription_ns.abort(404, f"No active subscription found for user")
        
        # Don't allow changing to the same plan
        if subscription.plan_id == new_plan.id:
            subscription_ns.abort(400, f"User is already subscribed to this plan")
        
        # Get the current plan for price comparison
        current_plan = SubscriptionPlan.query.get(subscription.plan_id)
        
        # Record whether this is an upgrade or downgrade
        is_upgrade = new_plan.price > current_plan.price
        
        # Change the plan
        subscription.change_plan(new_plan.id, prorate=data.get('prorate', True))
        
        # Update subscription dates if interval/duration changed
        now = datetime.utcnow()
        
        # Recalculate end date based on new plan duration
        if new_plan.duration_months:
            # Add months to current date
            month = now.month - 1 + new_plan.duration_months
            year = now.year + month // 12
            month = month % 12 + 1
            end_date = datetime(year, month, min(now.day, 28), now.hour, now.minute, now.second)
            subscription.current_period_end = end_date
            subscription.end_date = end_date
        
        # Update payment status - in a real system this would involve payment processing
        subscription.payment_status = PaymentStatus.PAID.value
        
        # Save changes
        db.session.commit()
        
        return subscription 