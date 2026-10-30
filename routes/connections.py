from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, inspect
from pydantic import BaseModel
from typing import Optional
import json
from database.db import get_db
from models.models import DBConnection
from utils.auth import verify_token

router = APIRouter(prefix="/connections", tags=["DB Connections"])


class ConnectionRequest(BaseModel):
    name    : str
    db_type : str          # mysql, postgresql, sqlite
    host    : Optional[str] = "localhost"
    port    : Optional[int] = 3306
    username: Optional[str] = ""
    password: Optional[str] = ""
    db_name : str


def build_connection_url(data: ConnectionRequest) -> str:
    """
    Different databases  URLs formats:
    MySQL:      mysql+pymysql://user:pass@host:port/dbname
    PostgreSQL: postgresql://user:pass@host:port/dbname
    SQLite:     sqlite:///path/to/file.db
    """
    if data.db_type == "mysql":
        return f"mysql+pymysql://{data.username}:{data.password}@{data.host}:{data.port}/{data.db_name}"
    elif data.db_type == "postgresql":
        return f"postgresql://{data.username}:{data.password}@{data.host}:{data.port}/{data.db_name}"
    elif data.db_type == "sqlite":
        return f"sqlite:///{data.db_name}"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported database type: {data.db_type}")


def scan_database_schema(connection_url: str) -> dict:
    """
    Scaning the connected database and extract schema information.
    """
    engine    = create_engine(connection_url)
    inspector = inspect(engine)
    schema    = {}

    table_names = inspector.get_table_names()

    for table_name in table_names:
        columns = []
        # Get all columns for table
        for col in inspector.get_columns(table_name):
            columns.append({
                "name"    : col["name"],
                "type"    : str(col["type"]),
                "nullable": col.get("nullable", True)
            })

        # primary keys
        pk = inspector.get_pk_constraint(table_name)

        # foreign keys
        fks = inspector.get_foreign_keys(table_name)

        schema[table_name] = {
            "columns"      : columns,
            "primary_keys" : pk.get("constrained_columns", []),
            "foreign_keys" : [
                {
                    "column"          : fk["constrained_columns"],
                    "references_table": fk["referred_table"]
                }
                for fk in fks
            ]
        }

    engine.dispose()   
    return schema


@router.post("/add")
def add_connection(
    data         : ConnectionRequest,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """
    Add new database connection for the company.
    """
    company_id     = current_user["company_id"]
    connection_url = build_connection_url(data)

    # Test connection
    try:
        test_engine = create_engine(connection_url)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))   # simple test query
        test_engine.dispose()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot connect to database: {str(e)}"
        )

    # Scan schema
    try:
        schema = scan_database_schema(connection_url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot scan database schema: {str(e)}"
        )

    # Save to our database
    connection = DBConnection(
        company_id   = company_id,
        name         = data.name,
        db_type      = data.db_type,
        host         = data.host,
        port         = data.port,
        username     = data.username,
        password_enc = data.password,   
        db_name      = data.db_name,
        schema_json  = json.dumps(schema)
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return {
        "message"       : "Database connected successfully!",
        "connection_id" : connection.id,
        "tables_found"  : len(schema),
        "tables"        : list(schema.keys()),
        "schema"        : schema
    }


@router.get("/list")
def list_connections(
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """Get all database connections for current company."""
    connections = db.query(DBConnection).filter(
        DBConnection.company_id == current_user["company_id"],
        DBConnection.is_active  == True
    ).all()

    return {
        "connections": [
            {
                "id"     : c.id,
                "name"   : c.name,
                "db_type": c.db_type,
                "db_name": c.db_name,
                "tables" : len(json.loads(c.schema_json)) if c.schema_json else 0
            }
            for c in connections
        ]
    }