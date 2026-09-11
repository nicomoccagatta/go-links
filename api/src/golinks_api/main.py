from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Go Links")


class LinkList(BaseModel):
    items: list[str]


@app.get("/api/links", response_model=LinkList)
def list_links() -> LinkList:
    return LinkList(items=[])
