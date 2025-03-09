from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import asyncio
from typing import List
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory storage
runways = [{"id": 1, "name": "Runway 1", "occupied": False}]
planes = []
clients = []  # WebSocket clients

class Plane(BaseModel):
    id: int
    name: str
    location: str
    status: str = "Waiting"  # Taxiing, In Air, Landed

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)

async def broadcast_update():
    data = {"planes": planes, "runways": runways}
    for client in clients:
        await client.send_json(data)

@app.get("/runways/")
def get_runways():
    return runways

@app.get("/planes/")
def get_planes():
    return planes

@app.post("/planes/")
async def register_plane(plane: Plane):
    for r in runways:
        if r["name"] == plane.location and r["occupied"]:
            raise HTTPException(status_code=400, detail="Runway occupied")
    
    planes.append(plane)
    for r in runways:
        if r["name"] == plane.location:
            r["occupied"] = True
    
    await broadcast_update()
    return plane

@app.put("/planes/{plane_id}/simulate-move")
async def simulate_plane_movement(plane_id: int, new_location: str):
    for plane in planes:
        if plane.id == plane_id:
            plane.status = "Taxiing"
            await broadcast_update()
            await asyncio.sleep(5)  # Simulate taxiing
            
            plane.status = "In Air"
            await broadcast_update()
            await asyncio.sleep(10)  # Simulate flying
            
            for r in runways:
                if r["name"] == new_location and r["occupied"]:
                    plane.status = "Holding in Air"
                    await broadcast_update()
                    return plane
            
            for r in runways:
                if r["name"] == plane.location:
                    r["occupied"] = False  # Free old runway
                if r["name"] == new_location:
                    r["occupied"] = True  # Occupy new runway

            plane.location = new_location
            plane.status = "Landed"
            await broadcast_update()
            return plane
    
    raise HTTPException(status_code=404, detail="Plane not found")
