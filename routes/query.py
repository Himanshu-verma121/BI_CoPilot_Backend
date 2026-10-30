from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import time                                         
from database.db import get_db
from models.models import DBConnection, Conversation
from utils.auth import verify_token
from utils.cache import get_cached_result, set_cached_result  
from ai.query_engine import QueryEngine
from config import settings

router    = APIRouter(prefix="/query", tags=["Query"])
ai_engine = QueryEngine()


class QueryRequest(BaseModel):
    question      : str
    connection_id : int
    use_cache     : bool = True     


@router.post("/ask")
def ask_question(
    data         : QueryRequest,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    company_id = current_user["company_id"]

    # Database connection
    connection = db.query(DBConnection).filter(
        DBConnection.id         == data.connection_id,
        DBConnection.company_id == company_id,
        DBConnection.is_active  == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code = 404,
            detail      = "Database connection not found"
        )

    # Checking Redis Cache
    if data.use_cache:
        cached = get_cached_result(
            company_id    = company_id,
            connection_id = data.connection_id,
            question      = data.question
        )
        if cached:
            print(f"Returning cached result")
            return cached

    # Building connection URL 
    if connection.db_type == "mysql":
        url = f"mysql+pymysql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    elif connection.db_type == "postgresql":
        url = f"postgresql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    else:
        url = f"sqlite:///{connection.db_name}"

    schema = json.loads(connection.schema_json)

    # Conversation history
    history = db.query(Conversation).filter(
        Conversation.company_id    == company_id,
        Conversation.connection_id == data.connection_id
    ).order_by(
        Conversation.created_at.desc()
    ).limit(5).all()

    history_list = [
        {"question": h.question, "sql": h.sql_generated}
        for h in reversed(history)
    ]

    # AI Query
    # Execution time 
    start_time = time.time()

    result = ai_engine.process_question(
        question       = data.question,
        connection_url = url,
        schema         = schema,
        history        = history_list
    )

    # How long query took in milliseconds
    execution_ms = int((time.time() - start_time) * 1000)
    result["execution_ms"] = execution_ms
    result["was_cached"]   = False

    # Save to Cache 
    if not result.get("error") and data.use_cache:
        set_cached_result(
            company_id    = company_id,
            connection_id = data.connection_id,
            question      = data.question,
            result        = result,
            ttl_seconds   = 3600    
        )

    # Save to conversation history 
    conv = Conversation(
        company_id    = company_id,
        user_id       = current_user["user_id"],
        connection_id = data.connection_id,
        question      = data.question,
        sql_generated = result.get("sql"),
        answer        = result.get("answer"),
        chart_type    = result.get("chart_type"),
        chart_data    = json.dumps(result.get("chart")) if result.get("chart") else None,
        execution_ms  = execution_ms,
        was_cached    = False
    )
    db.add(conv)
    db.commit()

    return result


# Cache Management Endpoints 
@router.delete("/cache/clear/{connection_id}")
def clear_cache(
    connection_id : int,
    db            : Session = Depends(get_db),
    current_user  : dict    = Depends(verify_token)
):
    from utils.cache import delete_cached_results
    delete_cached_results(
        company_id    = current_user["company_id"],
        connection_id = connection_id
    )
    return {"message": "Cache cleared successfully"}


@router.get("/cache/stats")
def cache_stats(current_user: dict = Depends(verify_token)):
    from utils.cache import get_cache_stats
    return get_cache_stats()