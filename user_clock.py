import motor.motor_asyncio

from fastapi import FastAPI, Body, Query
from bson import ObjectId
from pydantic import BaseModel
from fastapi import HTTPException
from typing import Optional,List
from datetime import date

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
db = client.get_database("orders")
collection = db.get_collection("user_clock")

app = FastAPI()

class Createrecord(BaseModel):
    email: str
    location: str

class ItemUpdate(BaseModel):
    email: Optional[str] = None
    location: Optional[str] = None

def serialize_item(item):
    """Convert ObjectId to string in the item dictionary."""
    if item is not None:
        item["_id"] = str(item["_id"])  # Convert ObjectId to string
    return item

@app.post("/create_clock_record/", response_description="this is to create item", response_model=Createrecord)
async def create_item(item: Createrecord = Body(...)):
    try:
        data = item.dict()
        data["inserted_date"] = str(date.today())
        new_item = await collection.insert_one(data)
        created_item = await collection.find_one({"_id": new_item.inserted_id})
        serialized_item = serialize_item(created_item)
        return serialized_item
    except Exception as error:
        return {str(error)}

@app.get("/retrieve_item/{item_id}", response_description="This API retrieves the item based on the ObjectId provided")
async def retrieve_item(item_id: str):
    # Check if item_id is a valid ObjectId
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")
    # Try to retrieve the item from the database
    item = await collection.find_one({"_id": obj_id})
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    # Serialize item to ensure ObjectId is converted to string
    serialized_item = serialize_item(item)
    return serialized_item

@app.get("/items/filter", response_description="Filter items based on criteria")
async def filter_item(
    email: Optional[str] = Query(None),
    location: Optional[int] = Query(None),
):
    query = {}

    if email:
        query["email"] = email
    if location:
        query["location"] = location
    try:
        # Use to_list() to retrieve documents asynchronously
        items = await collection.find(query).to_list(length=None)
        serialized_items = [serialize_item(item) for item in items]
        return serialized_items
    except Exception as error:
        # Log the error or raise HTTPException
        raise HTTPException(status_code=500, detail=str(error))


@app.delete("/items/{item_id}/", response_description="Delete an item by ID")
async def delete_item(item_id: str):
    # Convert item_id to ObjectId
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    # Check if the item exists
    existing_item = await collection.find_one({"_id": obj_id})
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete the item from the database
    result = await collection.delete_one({"_id": obj_id})

    # Check if the delete was successful
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"detail": "Item deleted successfully"}

@app.put("/items/{item_id}", response_description="Update an item by ID")
async def update_item(item_id: str, item_update: ItemUpdate):
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    # Build the update query
    update_data = {k: v for k, v in item_update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Update the document in MongoDB
    result = await collection.update_one({"_id": obj_id}, {"$set": update_data})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    # Retrieve the updated document
    updated_item = await collection.find_one({"_id": obj_id})
    return {"message": "Item updated successfully", "item": serialize_item(updated_item)}
