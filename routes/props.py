from fastapi import APIRouter
from models.schemas import PropList

router = APIRouter(tags=["props"])


@router.get("/props/today", response_model=PropList)
def get_props_today():
    # TODO: query PropEdge DB for today's props
    return PropList(props=[])
