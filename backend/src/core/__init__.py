"""Core application package.

Modules are imported explicitly by their consumers. Keeping this package
initializer side-effect free prevents circular imports during Alembic model
loading and application startup.
"""
