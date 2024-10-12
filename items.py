
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Body, Query
from bson import ObjectId
from pydantic import BaseModel
from fastapi import HTTPException
from typing import Optional,List
from datetime import date


class CreateItem(BaseModel):
    name: str
    email: str
    item_name: str
    quantity: int
    expiry_date: str


class UpdateItem(BaseModel):
    name: str
    item_name: str
    quantity: int
    expiry_date: str


app = FastAPI()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["orders"]
item_collection = db["items"]


def serialize_item(item):
    """Convert ObjectId to string in the item dictionary."""
    if item is not None:
        item["_id"] = str(item["_id"])  # Convert ObjectId to string
    return item

@app.put("/items/{item_id}", response_description="Update an item's details by ID")
async def update_item(item_id: str, item: CreateItem = Body(...)):
    # Convert item_id to ObjectId
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    # Prepare the update data, excluding insert_date
    update_data = item.dict(exclude={"insert_date"})

    # Check if the item exists
    existing_item = await item_collection.find_one({"_id": obj_id})
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Update the item in the database
    result = await item_collection.update_one({"_id": obj_id}, {"$set": update_data})

    # Check if the update was successful
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Update failed")

    # Retrieve the updated item
    updated_item = await item_collection.find_one({"_id": obj_id})
    return serialize_item(updated_item)


@app.post("/create_item/", response_description="this is to create item", response_model=CreateItem)
async def create_item(item: CreateItem = Body(...)):
    try:
        data = item.dict()
        data["inserted_date"] = str(date.today())
        new_item = await item_collection.insert_one(data)
        created_item = await item_collection.find_one({"_id": new_item.inserted_id})
        return created_item
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
    item = await item_collection.find_one({"_id": obj_id})
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    # Serialize item to ensure ObjectId is converted to string
    serialized_item = serialize_item(item)
    return serialized_item


@app.get("/items/filter", response_description="Filter items based on criteria")
async def filter_item(
    email: Optional[str] = Query(None),
    expiry_date: Optional[date] = Query(None),
    insert_date: Optional[date] = Query(None),
    quantity: Optional[int] = Query(None),
):
    query = {}

    if email:
        query["email"] = email
    if expiry_date:
        query["expiry_date"] = {"$gt": expiry_date.isoformat()}  # Convert to ISO string if stored as string
    if insert_date:
        query["insert_date"] = {"$gt": insert_date.isoformat()}  # Convert to ISO string if stored as string
    if quantity is not None:
        query["quantity"] = {"$gte": quantity}

    try:
        # Use to_list() to retrieve documents asynchronously
        items = await item_collection.find(query).to_list(length=None)
        serialized_items = [serialize_item(item) for item in items]
        return serialized_items
    except Exception as error:
        # Log the error or raise HTTPException
        raise HTTPException(status_code=500, detail=str(error))


class EmailCount(BaseModel):
    email: str
    count: int

@app.get("/items/count_by_email", response_model=List[EmailCount])
async def count_items_by_email():
    pipeline = [
        {
            "$group": {
                "_id": "$email",  # Group by the 'email' field
                "count": {"$sum": 1}  # Count the number of items for each email
            }
        },
        {
            "$project": {
                "email": "$_id",  # Rename _id to email
                "count": 1,  # Include the count field
                "_id": 0  # Exclude the default _id field from the output
            }
        }
    ]

    result = await item_collection.aggregate(pipeline).to_list(length=None)
    return result

@app.delete("/items/{item_id}/", response_description="Delete an item by ID")
async def delete_item(item_id: str):
    # Convert item_id to ObjectId
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    # Check if the item exists
    existing_item = await item_collection.find_one({"_id": obj_id})
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete the item from the database
    result = await item_collection.delete_one({"_id": obj_id})

    # Check if the delete was successful
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"detail": "Item deleted successfully"}