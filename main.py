import logging 
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime


# load the environment variables inside of this .env file
load_dotenv()

# Create clients
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,

    #define the types of diiferent variables in this dynamic typed programming language
    serializer=inngest.PydanticSerializer() 
)

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    return {"message": "hello World!"}


app = FastAPI()

@app.get("/")
async def root():
    # Default root endpoint to verify the server is running
    return {"message": "api is running doohhhhh <3"}

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])