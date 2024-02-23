# from sys import maxsize
from typing import List
from fastapi import FastAPI, Response, Depends, status
from sqlalchemy import DateTime, ForeignKey, func, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import os

DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_HOST = os.environ.get("DB_HOST")
PORT = os.environ.get("PORT")

## DB
engine = create_async_engine(f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}", pool_size=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    limits: Mapped[int] = mapped_column(nullable=False)
    initial_balance: Mapped[int] = mapped_column(nullable=False)
    actual_balance: Mapped[int] = mapped_column(nullable=False)
    transactions: Mapped[List["Transaction"]] = relationship()

    # __mapper_args__ = {"eager_defaults": True}

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[int] = mapped_column(nullable=False)
    transaction_type: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))


async def get_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

class TransactionIn(BaseModel):
    valor: int
    tipo: str
    descricao: str

## FAST API
app = FastAPI()

@app.post("/clientes/{client_id}/transacoes")
async def transaction(client_id: int, txin: TransactionIn, response: Response, db: AsyncSession = Depends(get_db)):


    if len(txin.descricao) > 10:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {"error": "description cant be higher than 10"}
    
    if txin.valor < 0:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {"error": "invalid value"}

    res = await db.execute(select(Client).where(Client.id == client_id))

    client = res.scalar()

    if not client:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "client not found"}

    new_balance = 0

    match txin.tipo:
        case "d":
            new_balance = client.actual_balance - txin.valor
        case "c":
            new_balance = client.actual_balance + txin.valor
        case _:
            response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            return {"error": "invalid transaction type"}

    transaction = Transaction(value=txin.valor, transaction_type=txin.tipo, description=txin.descricao, client_id=client_id)

    if (client.limits + new_balance) < 0:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {"error": "limit exceeded"}

    client.actual_balance = new_balance

    db.add(transaction)
    await db.commit()

    return {
        "limite": client.limits,
        "saldo": client.actual_balance
    }

@app.get("/clientes/{client_id}/extrato")
async def extract(client_id: int, response: Response, db: AsyncSession = Depends(get_db)):

    res = await db.execute(select(Client).where(Client.id == client_id))

    client = res.scalar()

    if not client:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "client not found"}

    res = await db.execute(select(Transaction).where(Transaction.client_id == client_id).order_by(Transaction.completed_at.desc()))

    transactions = res.scalars().all()
    count = 0
    last_txs = []

    for tx in transactions:
        count+=1

        last_txs.append({
            "valor": tx.value,
            "tipo": tx.transaction_type,
            "descricao": tx.description,
            "realizada_em": tx.completed_at
        })

        if count == 10:
            break

    return {
        "saldo": {
            "total": client.actual_balance,
            "data_extrato": datetime.now(),
            "limite": client.limits
        },
        "ultimas_transacoes": last_txs
    }

def main():
    port = int(PORT or 8000)
    uvicorn.run("main:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
