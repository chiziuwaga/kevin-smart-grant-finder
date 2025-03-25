"""
Dashboard routes and views.
"""

from flask import Blueprint, render_template, jsonify
from database.models import Grant, Analysis

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
def index():
    return render_template('dashboard/index.html')

@dashboard.route('/api/grants')
def get_grants():
    # TODO: Implement grant listing
    return jsonify({
        'grants': []
    })

@dashboard.route('/api/analytics')
def get_analytics():
    # TODO: Implement analytics
    return jsonify({
        'total_grants': 0,
        'total_amount': 0,
        'success_rate': 0
    })