from fastapi import APIRouter
from models.schemas import KeyProvisionRequest, KeyProvisionResponse

router = APIRouter(tags=["keys"])


@router.post("/keys/provision", response_model=KeyProvisionResponse)
def provision_key(body: KeyProvisionRequest):
    # TODO: generate and store API key
    raise NotImplementedError("Key provisioning not yet implemented")
