import os
from typing import Annotated, Any

import uvicorn
from auth import Caller, verify
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from pymongo import MongoClient

app = FastAPI()
items = MongoClient(os.environ["MONGO_URL"]).menu.items


class Item(BaseModel):
    restaurantId: str
    name: str = Field(min_length=1)
    price: int = Field(ge=0)
    available: bool = True


def with_id(document: dict[str, Any]) -> dict[str, Any]:
    document["id"] = str(document.pop("_id"))
    return document


def object_id(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except InvalidId:
        raise HTTPException(404)


def stored(item_id: str) -> dict[str, Any]:
    document = items.find_one({"_id": object_id(item_id)})
    if document is None:
        raise HTTPException(404)
    return document


def require_owner(subject: str, restaurant_id: str) -> None:
    if subject != restaurant_id:
        raise HTTPException(403)


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, e: RequestValidationError):
    return Response(status_code=400)


@app.get("/health")
def health():
    return Response(status_code=200)


@app.post("/items")
def create(item: Item, caller: Annotated[Caller, Depends(verify)]):
    require_owner(caller.subject, item.restaurantId)
    document = item.model_dump()
    items.insert_one(document)
    return with_id(document)


@app.get("/items")
def by_restaurant(
    restaurant_id: Annotated[str, Query(alias="restaurantId")],
    caller: Annotated[Caller, Depends(verify)],
):
    return [
        with_id(document) for document in items.find({"restaurantId": restaurant_id})
    ]


@app.get("/items/{item_id}")
def get(item_id: str, caller: Annotated[Caller, Depends(verify)]):
    return with_id(stored(item_id))


@app.put("/items/{item_id}")
def update(item_id: str, item: Item, caller: Annotated[Caller, Depends(verify)]):
    require_owner(caller.subject, item.restaurantId)
    require_owner(caller.subject, stored(item_id)["restaurantId"])
    replaced = items.replace_one({"_id": object_id(item_id)}, item.model_dump())
    if replaced.matched_count == 0:
        raise HTTPException(404)
    return {"id": item_id, **item.model_dump()}


@app.delete("/items/{item_id}")
def delete(item_id: str, caller: Annotated[Caller, Depends(verify)]):
    require_owner(caller.subject, stored(item_id)["restaurantId"])
    items.delete_one({"_id": object_id(item_id)})
    return Response(status_code=200)


@app.delete("/items")
def delete_by_restaurant(
    restaurant_id: Annotated[str, Query(alias="restaurantId")],
    caller: Annotated[Caller, Depends(verify)],
):
    require_owner(caller.subject, restaurant_id)
    items.delete_many({"restaurantId": restaurant_id})
    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
