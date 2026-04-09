from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from env.environment import AutonomousTrafficControlEnvironment
from env.models import ReviewAction, ReviewObservation, ReviewState


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action: Dict[str, Any] = Field(default_factory=dict)


def _to_step_payload(observation: ReviewObservation) -> Dict[str, Any]:
    obs_data = observation.model_dump()
    reward = float(obs_data.pop("reward", 0.0) or 0.0)
    done = bool(obs_data.pop("done", False))
    return {
        "observation": obs_data,
        "reward": reward,
        "done": done,
    }


def _build_app() -> FastAPI:
    app = FastAPI(
        title="Autonomous Traffic Control OpenEnv",
        version="1.0.0",
        description=(
            "Multi-agent environment where AI systems manage a 4-way intersection "
            "with emergency vehicle prioritization."
        ),
    )

    http_env = AutonomousTrafficControlEnvironment()

    @app.get("/")
    async def root() -> Dict[str, Any]:
        return {
            "name": "autonomous_traffic_control_env",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
        }

    @app.post("/reset")
    async def reset(request: ResetRequest = Body(default=ResetRequest())) -> Dict[str, Any]:
        obs = http_env.reset(task_id=request.task_id)
        return _to_step_payload(obs)

    @app.post("/step")
    async def step(request: StepRequest) -> Dict[str, Any]:
        try:
            action = ReviewAction(**request.action)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        obs, _, _, _ = http_env.step(action)
        return _to_step_payload(obs)

    @app.get("/state")
    async def state() -> Dict[str, Any]:
        try:
            current = http_env.state()
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return current.model_dump()

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "healthy"}

    @app.get("/metadata")
    async def metadata() -> Dict[str, str]:
        return {
            "name": "autonomous_traffic_control_env",
            "description": (
                "Multi-agent environment where AI systems manage a 4-way "
                "intersection with emergency vehicle prioritization."
            ),
            "version": "1.0.0",
        }

    @app.get("/schema")
    async def schema() -> Dict[str, Any]:
        return {
            "action": ReviewAction.model_json_schema(),
            "observation": ReviewObservation.model_json_schema(),
            "state": ReviewState.model_json_schema(),
        }

    @app.post("/mcp")
    async def mcp(_: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32601,
                "message": "MCP not implemented for this benchmark environment.",
            },
        }

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        ws_env = AutonomousTrafficControlEnvironment()

        try:
            while True:
                raw_message = await websocket.receive_text()
                try:
                    payload = json.loads(raw_message)
                    message_type = payload.get("type")
                    data = payload.get("data", {})
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {
                                "message": "Invalid JSON payload.",
                                "code": "INVALID_JSON",
                            },
                        }
                    )
                    continue

                if message_type == "reset":
                    obs = ws_env.reset(task_id=data.get("task_id"))
                    await websocket.send_json({"type": "observation", "data": _to_step_payload(obs)})
                elif message_type == "step":
                    try:
                        action = ReviewAction(**data)
                    except Exception as exc:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "data": {"message": str(exc), "code": "VALIDATION_ERROR"},
                            }
                        )
                        continue

                    obs, _, _, _ = ws_env.step(action)
                    await websocket.send_json({"type": "observation", "data": _to_step_payload(obs)})
                elif message_type == "state":
                    await websocket.send_json(
                        {"type": "state", "data": ws_env.state().model_dump()}
                    )
                elif message_type == "close":
                    break
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {
                                "message": "Unknown message type.",
                                "code": "UNKNOWN_TYPE",
                            },
                        }
                    )
        except WebSocketDisconnect:
            pass
        finally:
            ws_env.close()

    return app


app = _build_app()


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
