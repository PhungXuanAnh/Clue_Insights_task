# Profiling Slow Queries with Flask-DebugToolbar

This document explains how to use Flask-DebugToolbar to identify and optimize slow queries in our application.

## Setup

Flask-DebugToolbar has been integrated into the project for development environments. The toolbar automatically appears on HTML responses when running in debug mode (which is enabled by default in development).

## Accessing the Profiler

1. Run the application in development mode
2. Access any HTML endpoint (like `/api/docs` for Swagger UI)
3. The debug toolbar will appear on the right side of the page
4. Click on the "SQLAlchemy" tab to view executed queries
5. Click on the "Profiler" tab to view execution times

## Using the SQLAlchemy Panel

The SQLAlchemy panel shows:
- All executed queries
- Query execution time
- Context in which the query was executed
- Number of rows returned

This information helps identify:
- N+1 query problems
- Missing indexes
- Inefficient joins
- Redundant queries

## Using the Profiler Panel

The Profiler panel provides:
- Function-level profiling data
- Call hierarchy
- Execution time per function
- Cumulative time including nested calls

To enable the profiler for all requests:
1. Set `DEBUG_TB_PROFILER_ENABLED = True` (already configured)
2. Refresh the page to see profiling data

## Analyzing JSON API Endpoints

Since the debug toolbar only appears on HTML responses, we can use a special approach for profiling our API endpoints:

1. Use the SQLAlchemy echo feature (`SQLALCHEMY_ECHO = True`) which logs all SQL queries to the console
2. Examine Docker logs for query information: `docker logs --tail 100 clue_insights_task-app-1`
3. Look for slow-running queries and execution times

## Example Optimization Workflow

1. Identify slow queries using the debug toolbar
2. Examine the query execution plan using `EXPLAIN`
3. Add appropriate indexes to improve query performance
4. Consider using eager loading (`joinedload()`, `selectinload()`, etc.) for related data
5. For complex operations, consider raw SQL optimizations

## Notes

- The debug toolbar is only enabled in development mode
- Do not enable the debug toolbar in production
- Remember to check how API endpoints perform under load, not just in developer testing 