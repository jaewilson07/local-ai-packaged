"""Custom exceptions for the Lambda server.

This module defines custom exception classes used throughout the server.
"""


class LambdaServerException(Exception):
    """Base exception for Lambda server errors."""


class LLMException(LambdaServerException):
    """Exception raised when LLM operations fail."""


class MongoDBException(LambdaServerException):
    """Exception raised when MongoDB operations fail."""


class Neo4jException(LambdaServerException):
    """Exception raised when Neo4j operations fail."""


class AuthenticationException(LambdaServerException):
    """Exception raised when authentication fails."""


class ValidationException(LambdaServerException):
    """Exception raised when validation fails."""
