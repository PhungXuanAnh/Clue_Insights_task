"""
Routes for subscription plans and user subscriptions.
"""
import json
from datetime import datetime
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
from app.models.user_subscription import SubscriptionStatus, UserSubscription
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