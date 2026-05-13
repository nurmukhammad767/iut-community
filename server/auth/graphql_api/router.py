"""Minimal GraphQL POST endpoint backed by graphene.

We avoid pulling in `starlette-graphene3` / `ariadne` / `strawberry` to keep
the dependency surface minimal — graphene already ships in requirements.txt.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from jwt import get_current_user
from graphql_api.schema import schema


router = APIRouter(prefix="/graphql", tags=["GraphQL"])


@router.post("")
async def graphql_endpoint(
    payload: Dict[str, Any],
    _user: dict = Depends(get_current_user),
):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    variables = payload.get("variables") or {}
    operation_name = payload.get("operationName")

    result = schema.execute(
        query,
        variables=variables,
        operation_name=operation_name,
    )
    response: Dict[str, Any] = {"data": result.data}
    if result.errors:
        response["errors"] = [str(e) for e in result.errors]
    return response
