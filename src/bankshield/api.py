"""FastAPI REST API for BankShield transaction service."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from bankshield.collector import TransactionCollector

logger = logging.getLogger(__name__)

# Global collector instance
collector: TransactionCollector | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources on startup/shutdown."""
    global collector
    collector = TransactionCollector()
    if not collector.connect():
        logger.warning("Failed to connect to MongoDB on startup")
    yield
    if collector and collector.client:
        collector.client.close()


app = FastAPI(
    title="BankShield API",
    description="""
    ## BankShield Transaction API

    REST API для генерации и управления банковскими транзакциями.

    ### Функциональность:
    - Генерация синтетических транзакций
    - Запись транзакций в MongoDB
    - Получение статистики по транзакциям
    - Мониторинг состояния системы

    ### Интеграция:
    - MongoDB для хранения транзакций
    - PostgreSQL для аналитики (через Airflow ETL)
    - DBT для трансформации данных
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Pydantic models for API
class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    mongodb_connected: bool = Field(..., description="MongoDB connection status")
    timestamp: datetime = Field(..., description="Current timestamp")


class TransactionLocation(BaseModel):
    """Transaction location model."""

    country: str = Field(..., description="Country code")
    city: str = Field(..., description="City name")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")


class TransactionDeviceInfo(BaseModel):
    """Transaction device information model."""

    device_type: str = Field(..., description="Device type (mobile, desktop, tablet)")
    os: str = Field(..., description="Operating system")
    ip_address: str = Field(..., description="IP address")


class TransactionMetadata(BaseModel):
    """Transaction metadata model."""

    session_id: str = Field(..., description="Session identifier")
    user_agent: str = Field(..., description="User agent string")


class TransactionResponse(BaseModel):
    """Transaction response model."""

    timestamp: datetime = Field(..., description="Transaction timestamp")
    transaction_id: str = Field(..., description="Unique transaction identifier")
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(..., description="Currency code (USD, EUR, RUB)")
    transaction_type: str = Field(
        ...,
        description="Transaction type (debit, credit, transfer, withdrawal, deposit)",
    )
    merchant_category: str = Field(..., description="Merchant category")
    merchant_name: str = Field(..., description="Merchant name")
    location: TransactionLocation = Field(..., description="Transaction location")
    device_info: TransactionDeviceInfo = Field(..., description="Device information")
    is_fraud: bool = Field(..., description="Fraud flag")
    risk_score: float = Field(..., ge=0, le=1, description="Risk score (0-1)")
    metadata: TransactionMetadata = Field(..., description="Transaction metadata")


class TransactionCreateRequest(BaseModel):
    """Request model for creating a custom transaction."""

    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    transaction_type: str = Field(default="debit", description="Transaction type")
    merchant_category: str = Field(default="online", description="Merchant category")
    is_fraud: bool = Field(default=False, description="Fraud flag")


class TransactionCreateResponse(BaseModel):
    """Response model for created transaction."""

    success: bool = Field(..., description="Operation success status")
    transaction_id: str = Field(..., description="Created transaction ID")
    message: str = Field(..., description="Status message")


class StatsResponse(BaseModel):
    """Statistics response model."""

    total_transactions: int = Field(..., description="Total number of transactions")
    fraud_transactions: int = Field(
        ..., description="Number of fraudulent transactions"
    )
    fraud_rate: float = Field(..., description="Fraud rate percentage")
    total_amount: float = Field(..., description="Total transaction amount")
    avg_amount: float = Field(..., description="Average transaction amount")
    unique_users: int = Field(..., description="Number of unique users")


class GenerateBatchResponse(BaseModel):
    """Response model for batch generation."""

    success: bool = Field(..., description="Operation success status")
    generated_count: int = Field(..., description="Number of generated transactions")
    inserted_count: int = Field(..., description="Number of inserted transactions")
    message: str = Field(..., description="Status message")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current status of the service and MongoDB connection.
    """
    mongodb_connected = False
    if collector and collector.client:
        try:
            collector.client.admin.command("ping")
            mongodb_connected = True
        except Exception:
            mongodb_connected = False

    return HealthResponse(
        status="healthy" if mongodb_connected else "degraded",
        mongodb_connected=mongodb_connected,
        timestamp=datetime.utcnow(),
    )


@app.get(
    "/transactions/generate", response_model=TransactionResponse, tags=["Transactions"]
)
async def generate_transaction() -> dict[str, Any]:
    """
    Generate a single synthetic transaction.

    Returns a randomly generated transaction without saving to database.
    Use POST /transactions to generate and save.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")

    transaction = collector.generate_transaction()
    return transaction


@app.post(
    "/transactions", response_model=TransactionCreateResponse, tags=["Transactions"]
)
async def create_transaction(
    request: TransactionCreateRequest | None = None,
) -> TransactionCreateResponse:
    """
    Generate and save a transaction to MongoDB.

    If request body is provided, uses the specified parameters.
    Otherwise, generates a random synthetic transaction.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Try to reconnect if collection is None
    if collector.collection is None:
        if not collector.connect():
            raise HTTPException(status_code=503, detail="MongoDB not connected")

    # Generate transaction
    transaction = collector.generate_transaction()

    # Override with custom values if provided
    if request:
        transaction["user_id"] = request.user_id
        transaction["amount"] = request.amount
        transaction["currency"] = request.currency
        transaction["transaction_type"] = request.transaction_type
        transaction["merchant_category"] = request.merchant_category
        transaction["is_fraud"] = request.is_fraud

    # Insert to MongoDB
    try:
        success = collector.insert_data(transaction)
        if success:
            return TransactionCreateResponse(
                success=True,
                transaction_id=transaction["transaction_id"],
                message="Transaction created successfully",
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to insert transaction")
    except Exception as e:
        logger.error(f"Error inserting transaction: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to insert transaction: {str(e)}"
        )


@app.post(
    "/transactions/batch", response_model=GenerateBatchResponse, tags=["Transactions"]
)
async def generate_batch(
    count: int = Query(
        default=10, ge=1, le=1000, description="Number of transactions to generate"
    ),
) -> GenerateBatchResponse:
    """
    Generate and save multiple transactions to MongoDB.

    Useful for quickly populating the database with test data.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Try to reconnect if collection is None
    if collector.collection is None:
        if not collector.connect():
            raise HTTPException(status_code=503, detail="MongoDB not connected")

    inserted = 0
    for _ in range(count):
        transaction = collector.generate_transaction()
        try:
            if collector.insert_data(transaction):
                inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert transaction: {e}")

    return GenerateBatchResponse(
        success=inserted > 0,
        generated_count=count,
        inserted_count=inserted,
        message=f"Generated {count} transactions, inserted {inserted}",
    )


@app.get("/transactions/stats", response_model=StatsResponse, tags=["Transactions"])
async def get_stats() -> StatsResponse:
    """
    Get transaction statistics from MongoDB.

    Returns aggregated metrics about all transactions in the database.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Try to reconnect if collection is None
    if collector.collection is None:
        if not collector.connect():
            raise HTTPException(status_code=503, detail="MongoDB not connected")

    try:
        # Aggregation pipeline for statistics
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_transactions": {"$sum": 1},
                    "fraud_transactions": {"$sum": {"$cond": ["$is_fraud", 1, 0]}},
                    "total_amount": {"$sum": "$amount"},
                    "avg_amount": {"$avg": "$amount"},
                    "unique_users": {"$addToSet": "$user_id"},
                }
            }
        ]

        result = list(collector.collection.aggregate(pipeline))

        if not result:
            return StatsResponse(
                total_transactions=0,
                fraud_transactions=0,
                fraud_rate=0.0,
                total_amount=0.0,
                avg_amount=0.0,
                unique_users=0,
            )

        stats = result[0]
        total = stats.get("total_transactions", 0)
        fraud = stats.get("fraud_transactions", 0)

        return StatsResponse(
            total_transactions=total,
            fraud_transactions=fraud,
            fraud_rate=round((fraud / total * 100) if total > 0 else 0, 2),
            total_amount=round(stats.get("total_amount", 0), 2),
            avg_amount=round(stats.get("avg_amount", 0), 2),
            unique_users=len(stats.get("unique_users", [])),
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {e}")


@app.get("/transactions/recent", response_model=list[dict], tags=["Transactions"])
async def get_recent_transactions(
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of transactions to return"
    ),
) -> list[dict]:
    """
    Get recent transactions from MongoDB.

    Returns the most recent transactions ordered by timestamp.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Try to reconnect if collection is None
    if collector.collection is None:
        if not collector.connect():
            raise HTTPException(status_code=503, detail="MongoDB not connected")

    try:
        transactions = list(
            collector.collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        )
        return transactions

    except Exception as e:
        logger.error(f"Error getting recent transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {e}")


def main() -> None:
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "bankshield.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
