import pathlib
from datetime import datetime, timedelta, timezone
import passlib
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient
from bson import Decimal128
from contextlib import asynccontextmanager
import json
import markdown
import aiohttp
import time
import uvicorn
from bson import ObjectId
from fastapi import FastAPI, Request, Depends, status, Response, Cookie, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks, File, UploadFile, HTTPException
from decimal import Decimal
import copy


from models import UploadedFile, Upload, UploadStatus, Query, AuthLink, DrillDown, Money, Transaction

MAX_FILE_SIZE = 1_000_000  # 1MB
FILE_DOWNLOAD_URL_VALID_TIME = timedelta(days=365)
# VIWEPOINTS_LIST_ID = "161fe277-70af-4b53-a527-4a88add18b1f"  
# USER_ID = 'facd7320-a53d-4ac2-bf8d-741dcd83ba87' #TODO: hardcoded for now


BASE_DIR = pathlib.Path(__file__).resolve().parent  # app
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create aiohttp session
    app.aiohttp_session = aiohttp.ClientSession()
    # Close aiohttp session
    await app.aiohttp_session.close()


app = FastAPI(lifespan=lifespan)  # TODO (openapi_url=None) or (docs_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Endpoints

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user_id = get_user_id_from_request(request)
    cookies_confirmed = is_cookies_confirmed(request)

    if user_id:
        return RedirectResponse(url=f"/feed")
    
    context = dict(request=request, cookies_confirmed=cookies_confirmed)
    response = templates.TemplateResponse("index.html", context=context)
    # Point browser to do not store cache
    response.headers["Cache-Control"] = "no-store"

    return response


@app.get("/drill-down/9ffe20c3-6199-4b7c-b77a-7784b35be822")
async def home_page_serve():
    return FileResponse(
        "static/drill-down.html", 
        media_type='text/html',
        headers={"Cache-Control": "no-store"}
    )


@app.get("/login/{auth_link}", response_class=HTMLResponse)
async def login(auth_link: str, request: Request, background_tasks: BackgroundTasks):
    # Simulate a dummy user
    dummy_user = {
        "user_id": "dummy_user_id",
        "cookies_confirmed": False,
        "auth_links": [{"auth_link": auth_link, "access_token_assigned": False}]
    }

    # Check if the auth_link matches the dummy user
    if auth_link == "expected_auth_link":  # Replace with the expected auth link for the dummy user
        user_id = dummy_user.get("user_id")

        # Create new token for user after logging in
        new_token = create_access_token_for_user(user_id=user_id)
        context = dict(request=request, token=new_token)
        response = templates.TemplateResponse("authorization/code-accepted.html", context)

        # Set new token
        response = set_token_to_browser(response, 'access_token', new_token)

        # Set cookies_confirmed token if it is not set
        cookies_confirmed = is_cookies_confirmed(request)
        if cookies_confirmed:
            if not dummy_user.get("cookies_confirmed"):
                dummy_user["cookies_confirmed"] = True
        else:
            cookies_confirmed = dummy_user.get("cookies_confirmed")
            cookies_confirmed_token = create_cookies_confirmed_token(cookies_confirmed=cookies_confirmed)
            response = set_token_to_browser(response, 'cookies', cookies_confirmed_token)

        # Point browser to do not store cache
        response.headers["Cache-Control"] = "no-store"

        return response

    # If user is not found, return invalid code page
    context = dict(request=request)
    response = templates.TemplateResponse("authorization/invalid-code.html", context)

    return response 


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request, background_tasks: BackgroundTasks):
    user_id = get_user_id_from_request(request)
    response = RedirectResponse(url="/")

    if user_id:
        # Delete token from browser
        response.delete_cookie(
            key="access_token", secure=False, httponly=True, samesite="lax"
        )
        
    # Point browser to do not store cache
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/start-query")
async def root(request: Request):
    user_id = get_user_id_from_request(request)
    
    # Static dummy data for viewpoints
    viewpoints = [
        {"viewpoint_id": "1", "text_on_checkbox": "Viewpoint 1", "viewpoint": "Description of viewpoint 1"},
        {"viewpoint_id": "2", "text_on_checkbox": "Viewpoint 2", "viewpoint": "Description of viewpoint 2"},
        {"viewpoint_id": "3", "text_on_checkbox": "Viewpoint 3", "viewpoint": "Description of viewpoint 3"},
    ]
    
    # Simulating user retrieval
    user = {"user_id": user_id, "view_points_list": "dummy_list_id"}  # Dummy user data

    if user:
        context = dict(request=request, user=user, viewpoints=viewpoints)
        response = templates.TemplateResponse("lambda-upload.html", context=context)
        # Point browser to do not store cache
        response.headers["Cache-Control"] = "no-store"

        return response
    
    return templates.TemplateResponse("not-found.html", context=dict(request=request))


@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...), upload_id: str = Form(...)):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    if user:
        files = [file for file in files if file.filename]
        # file size check added
        if len(files) > 5:
            return JSONResponse(status_code=400, content={"message": "You can only upload a maximum of 5 files."})
        # file size check end
        if files:
            upload_id = upload_id if upload_id != ' ' else None

            if upload_id:
                upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
            else:
                # Create new upload
                upload = Upload(user_id=user_id, selected_viewpoints=[]).model_dump()
                # Create new container
                blob_service_client.create_container(upload['upload_id'])
            
            uploaded_files = []
            for file in files:
                # Check size of file not more than 1MB
                if file.size > MAX_FILE_SIZE:
                    return JSONResponse(status_code=400, content={"message": "File size too large."})
                elif file.content_type not in ['image/png', 'image/jpeg']:
                    return JSONResponse(status_code=400, content={"message": "File type not supported."})
                
                uploaded_file = UploadedFile(
                    name=file.filename,
                    size=file.size,
                    type=file.content_type
                ).model_dump()

                uploaded_file['download_url'] = generate_image_url(container=upload['upload_id'], blob=uploaded_file['file_id'], valid_time=FILE_DOWNLOAD_URL_VALID_TIME)
                # Add file to container
                blob = blob_service_client.get_blob_client(container=upload['upload_id'], blob=uploaded_file['file_id'])
                blob.upload_blob(file.file)

                uploaded_files.append(uploaded_file)
            
            upload['files'] += uploaded_files 
            uploaded_files = [file for file in uploaded_files]
            if upload_id:
                await app.mongodb['uploads'].update_one({"upload_id": upload_id}, {"$set": {"files": upload['files']}})
            else:
                await app.mongodb['uploads'].insert_one(upload)
                await app.mongodb['users'].update_one({"user_id": user_id}, {"$push": {"uploads": upload['upload_id']}})

            return Response(status_code=200, content=json.dumps({"upload_id": upload['upload_id'], "files": [dict(name=file['name'], size=file['size'], download_url=file['download_url']) for file in uploaded_files]}))
        
    return JSONResponse(status_code=400, content={"message": "No files uploaded."})


@app.post("/upload-confirmation")
async def upload_confirmation(request: Request, background_tasks: BackgroundTasks):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    json = await request.json()
    upload_id = json.get('upload_id') if json and json.get('upload_id') else None

    initial_query = json.get('initial_query') if json and json.get('initial_query') else None
    selected_viewpoints_ids = json.get('selected_viewpoints_ids') if json else None

    if upload_id == ' ' and selected_viewpoints_ids:
        view_points_list = await app.mongodb['viewpoints_lists'].find_one({"list_id": user.get('view_points_list')})
        selected_viewpoints = []
        for vw in view_points_list['viewpoints']:
            if vw['viewpoint_id'] in selected_viewpoints_ids:
                selected_viewpoints.append(vw)
        
        # Create new upload in db
        upload = Upload(
            user_id=user_id,
            selected_viewpoints=selected_viewpoints,
            initial_query=initial_query,
            status=UploadStatus.suggested_queries_generated.value
        )
        upload_id = upload.upload_id
        await app.mongodb['uploads'].insert_one(upload.model_dump())


    if user and upload_id and selected_viewpoints_ids:
        transaction_description = f'query {upload_id}'

        # Add upload_id to user's uploads if it is not there
        if upload_id not in user.get('uploads', []):
            await app.mongodb['users'].update_one({"user_id": user_id}, {"$push": {"uploads": upload_id}})

        viewpoints_document = await app.mongodb['viewpoints_lists'].find_one({"list_id": user.get('view_points_list')})
        if not viewpoints_document:
            return JSONResponse(status_code=400, content={"message": "No viewpoints found."})
        
        viewpoints = viewpoints_document.get('viewpoints') if viewpoints_document else None
        selected_viewpoints = [viewpoint for viewpoint in viewpoints if viewpoint['viewpoint_id'] in selected_viewpoints_ids]

        await app.mongodb['uploads'].update_one(
            {"upload_id": upload_id},
            {"$set": {
                "initial_query": initial_query,
                "selected_viewpoints": selected_viewpoints,
                "status": UploadStatus.screenshots_confirmed.value
            }}
        )

        # Process upload data
        upload_obj = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
        await process_upload_data(upload=upload_obj, upload_id=upload_id, selected_viewpoints=selected_viewpoints, background_tasks=background_tasks)

        await add_transaction(user_id=user_id, amount=Money(amount=Decimal128(f'-{str(user['query_price']['amount'])}'), currency=user['query_price']['currency']), description=transaction_description)
        return JSONResponse(status_code=200, content={"url_to_open": f"/suggested-queries/{upload_id}"})
    
    return JSONResponse(status_code=400, content={"message": "No upload_id or selected_viewpoints_ids provided."})


@app.post('/delete-file/{upload_id}/{file_id}')
async def delete_file(request: Request, upload_id: str, file_id: str):
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
    if upload:
        await app.mongodb['uploads'].update_one({"upload_id": upload_id}, {"$set": {"files.$[file].is_deleted": True}}, 
                                                array_filters=[{"file.file_id": file_id}])

    return Response(status_code=200)


@app.post('/cancel-upload/{upload_id}')
async def delete_file(request: Request, upload_id: str):
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
    if upload:
        await app.mongodb['uploads'].update_one({"upload_id": upload_id}, {"$set": {"status": UploadStatus.screenshots_cancelled.value }})

    return Response(status_code=200)


@app.get("/suggested-queries/{upload_id}")
async def query_screen(request: Request, upload_id: str, background_tasks: BackgroundTasks):
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
    text_to_display = upload.get('text_to_display') if upload else None
    suggested_queries = upload.get('suggested_queries') if upload else None

    if upload.get('user_query'):
        return RedirectResponse(url=f"/query-response/{upload_id}")

    if suggested_queries:
        context = dict(request=request, upload_id=upload_id, selected_viewpoints=upload['selected_viewpoints'],
                       text_to_display=text_to_display, suggested_queries=suggested_queries)
        return templates.TemplateResponse("query.html", context=context)
    
    return templates.TemplateResponse("not-found.html", context=dict(request=request))


@app.post("/submit-query/{upload_id}")
async def submit_query(request: Request, upload_id: str, background_tasks: BackgroundTasks):
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
    json = await request.json()
    query_text: str = json.get('query_text') if json else None
    draft_query_index: int | None = json.get('draft_query_index') if json else None
    draft_query_forwarded: bool = json.get('draft_query_forwarded') if json else False
    is_draft_query_edited: bool = json.get('is_draft_query_edited') if json else False
    #background_tasks.add_task(tools_call, query_text, upload_id)
    if upload and query_text:
        query_embedding = await get_text_embedding(query_text)
        image_embedding = [file.get('embedding') for file in upload.get('files', []) if file.get('embedding')]
        combined_embedding = [query_embedding] + image_embedding
    
        if draft_query_forwarded:
            relevant_results = await find_relevant_chunks_from_vectors(mongodb=app.mongodb, input_embeddings=combined_embedding, number_of_results=15,
                                                                    start_date=upload.get('suggested_queries', [])[draft_query_index].get('start_date'), 
                                                                    end_date=upload.get('suggested_queries', [])[draft_query_index].get('end_date'))
            upload['suggested_queries'][draft_query_index]['result'] = relevant_results
            upload['suggested_queries'][draft_query_index]['vectors'] = combined_embedding
            query_to_insert = upload['suggested_queries'][draft_query_index]
        else:
            relevant_results = await find_relevant_chunks_from_vectors(mongodb=app.mongodb, input_embeddings=combined_embedding, number_of_results=15)
            query_to_insert = Query(query=query_text, is_suggested_query=draft_query_forwarded, vectors=combined_embedding, result=relevant_results).model_dump()
        
        # new way
        query_to_insert['tool_calls'].extend(await tools_evaluator(query_text, chunks=query_to_insert['result'], tool_calls=query_to_insert['tool_calls'], keep_front_chars=False))
        query_to_insert['tool_calls'], temp_result_1 = await process_tool_calls(tools_list=query_to_insert['tool_calls'], upload_id=upload_id, http_session=app.aiohttp_session, mongodb=app.mongodb, exclude_chunks=query_to_insert['result'])
        query_to_insert['result'].extend(temp_result_1)
        query_to_insert['tool_calls'].extend(await tools_evaluator(query_text, chunks=query_to_insert['result'], tool_calls=query_to_insert['tool_calls'], keep_front_chars=False))
        query_to_insert['tool_calls'], temp_result_2 = await process_tool_calls(tools_list=query_to_insert['tool_calls'], upload_id=upload_id, http_session=app.aiohttp_session, mongodb=app.mongodb, exclude_chunks=query_to_insert['result'])
        query_to_insert['result'].extend(temp_result_2)
        query_to_insert['summary'] = await summarise_context(user_query=query_text, chunks=query_to_insert['result'], keep_front_chars=False)
        await app.mongodb['uploads'].update_one({"upload_id": upload_id}, {"$set": {"user_query": query_to_insert, "status": UploadStatus.query_submitted.value}})
        return Response(status_code=200)
    
    return Response(status_code=400)


@app.get("/query-response/{upload_id}") 
async def query_response(request: Request, upload_id: str):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})
    user = user if upload and upload['user_id'] == user_id else None

    if upload:
        if not upload.get('user_query'):
            return RedirectResponse(url=f"/suggested-queries/{upload_id}")
        
        upload['user_query']['summary'] = markdown.markdown(text=upload['user_query']['summary'], extensions=['extra']) if upload['user_query'].get('summary') is not None else ""
        for res_obj in upload.get('user_query').get('result'):
            if 'score' in res_obj:
                res_obj['score'] = round(res_obj['score'], 3)
            res_obj['date'] = res_obj['published']
            res_obj['published'] = res_obj['published'].strftime('%d %b %Y').lstrip('0')
            if res_obj.get('type') == 'table':
                res_obj['data'] = csv_string_to_html_table(res_obj['data'], external_origin=res_obj['external_origin']) if res_obj.get('data') else ''

        context = dict(request=request, user=user, upload=upload)
        response = templates.TemplateResponse("query-response.html", context=context)
        response.headers["Cache-Control"] = "no-store"
        return response
    
    response = templates.TemplateResponse("not-found.html", context=dict(request=request))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/result-selection/{upload_id}")
async def result_selection(request: Request, upload_id: str):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    json = await request.json()
    # print("selector logic")
    # print(json)

    if user and json:
        chunk_index = json.get('chunk_index')
        is_selected = json.get('is_selected')
        drilldown_id = json.get('drilldown_id')
        if chunk_index is not None: 
            if not drilldown_id:
                await app.mongodb['uploads'].update_one(
                    {"upload_id": upload_id},
                    {"$set": {f"user_query.result.{chunk_index}.is_selected": is_selected}}
                )
            else:
                await app.mongodb['uploads'].update_one(
                    {"upload_id": upload_id},
                    {"$set": {f"drill_downs.$[dd].result.{chunk_index}.is_selected": is_selected}},
                    array_filters=[
                        {"dd.drilldown_id": drilldown_id}
                    ]
                )

        return Response(status_code=200)
    return Response(status_code=400)
    

@app.post("/query-drilldown/{upload_id}")
async def query_drilldown(request: Request, upload_id: str):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    json = await request.json()
    upload = await app.mongodb['uploads'].find_one({"upload_id": upload_id})

    if user:
        query_text = json.get('query_text')
        # print(upload['user_query']['result'])
        #call drilldown function
        #query_embedding = await get_text_embedding(query_text)
        # selected_results = [
        #     copy.deepcopy(result) for result in upload['user_query']['result'] 
        #     if result.get('is_selected') #and not result.get('external_origin', False)
        # ]
        selected_results = None
        relevant_results = []
        if selected_results:
            # for i, cleaned_result in enumerate(selected_results):
            #     if cleaned_result.get('external_origin', False) and cleaned_result.get('type') in ['chart', 'table']:
            #         if cleaned_result.get('type') == 'chart':
            #             cleaned_result.pop('data', None)
            #         cleaned_result.pop('card_background_colour', None)
            #         cleaned_result.pop('type', None)
            #         cleaned_result.pop('external_origin', None)
            #         cleaned_result.pop('is_selected', None)
            query_text = f"""
            The Current User instruction is: {query_text};\n
            The Previous instruction was: {upload['user_query']['query']};\n
            Apply the Latest User instruction given the following context, that was selected by User: {selected_results}\n
            """
            # print(query_text)
            # print(selected_results)

            ### currently does nothing
            # all_external = all(upload['user_query']['result'][i].get('external_origin', False) == False for i in selected_cards)
            # if all_external:
            # combined_embedding = [query_embedding] + [result['embedding'] for result in selected_results if 'embedding' in result]
            # relevant_results = await find_relevant_chunks_from_vectors(mongodb=app.mongodb, input_embeddings=combined_embedding, 
            #                                                        exclude_chunks=upload['user_query']['result'], number_of_results=15)
            # else:
            #     combined_embedding = [query_embedding]
            #     relevant_results = await find_relevant_chunks_from_vectors(mongodb=app.mongodb, input_embeddings=combined_embedding, number_of_results=15)
            pass
        else:
            # combined_embedding = [query_embedding]
            # selected_results = upload['user_query']['result']
            #no of results was 6 here, 12 for all above
            # relevant_results = await find_relevant_chunks_from_vectors(mongodb=app.mongodb, input_embeddings=combined_embedding, number_of_results=15,
            #                                                            exclude_chunks=upload['user_query']['result'])
            pass
        upload['user_query']['tool_calls'].extend(await tools_evaluator(query_text, chunks=upload['user_query']['result'], tool_calls=upload['user_query']['tool_calls']))
        upload['user_query']['tool_calls'], temp_result_1 = await process_tool_calls(tools_list=upload['user_query']['tool_calls'], upload_id=upload_id, http_session=app.aiohttp_session, mongodb=app.mongodb, exclude_chunks=upload['user_query']['result'])
        # upload['user_query']['result'].extend(temp_result_1)
        upload['user_query']['result'] = temp_result_1 + upload['user_query']['result']
        upload['user_query']['tool_calls'].extend(await tools_evaluator(query_text, chunks=upload['user_query']['result'], tool_calls=upload['user_query']['tool_calls']))
        upload['user_query']['tool_calls'], temp_result_2 = await process_tool_calls(tools_list=upload['user_query']['tool_calls'], upload_id=upload_id, http_session=app.aiohttp_session, mongodb=app.mongodb, exclude_chunks=upload['user_query']['result'])
        upload['user_query']['result'] = temp_result_2 + upload['user_query']['result']
        # upload['user_query']['result'].extend(temp_result_2)
        # upload['user_query']['result'].extend(relevant_results)
        upload['user_query']['summary'] = await summarise_context(user_query=query_text, chunks=upload['user_query']['result'])


        new_drilldown = DrillDown(query=json.get('query_text'), is_suggested_query=False, #vectors=combined_embedding, 
                                    result=upload['user_query']['result'], 
                                    summary=str(upload['user_query']['summary']), 
                                    tool_calls=upload['user_query']['tool_calls'],
                                    user_id=user_id).model_dump()
        
        await app.mongodb['uploads'].update_one(
            {"upload_id": upload_id},
            {"$push": {
                    "drill_downs": new_drilldown,
                    #"tool_calls": {"$each": tools_list}
                }
            }
        )

        return JSONResponse(status_code=200, content={"drilldown_id": new_drilldown['drilldown_id']})
    
    return JSONResponse(status_code=400)


@app.get("/drill-down/{drilldown_id}")
async def query_drilldown(request: Request, drilldown_id: str):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})
    upload = await app.mongodb['uploads'].find_one({"drill_downs.drilldown_id": drilldown_id})
    user = user if upload and upload['user_id'] == user_id else None

    if upload:
        drilldown = next((dd for dd in upload['drill_downs'] if dd['drilldown_id'] == drilldown_id), None)
        if drilldown:
            drilldown['summary'] = markdown.markdown(text=drilldown['summary'], extensions=['extra']) if drilldown['summary'] is not None else ""
            for res_obj in drilldown.get('result'):
                if 'score' in res_obj:
                    res_obj['score'] = round(res_obj['score'], 3)
                res_obj['date'] = res_obj['published']
                res_obj['published'] = res_obj['published'].strftime('%d %b %Y').lstrip('0')
                if res_obj.get('type') == 'table':
                    res_obj['data'] = csv_string_to_html_table(res_obj['data'], external_origin=res_obj['external_origin']) if res_obj.get('data') else ''

            context = dict(request=request, user=user, upload=upload, drilldown=drilldown)
            response = templates.TemplateResponse("drilldown-response.html", context=context)
            response.headers["Cache-Control"] = "no-store"
            return response
    
    response = templates.TemplateResponse("not-found.html", context=dict(request=request))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/feed")
async def query_feed(request: Request):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})    

    if user:
        uploads_ids = user.get('uploads') if user else None
        uploads = await app.mongodb['uploads'].find({"upload_id": {"$in": uploads_ids}}).to_list(length=1000) if uploads_ids else None
        if uploads is not None and len(uploads) > 0:
            for upload in uploads:
                upload['uploaded_at'] = calculate_time_diff(upload['uploaded_at'])
                for drilldown in upload.get('drill_downs', []):
                    drilldown['timestamp'] = calculate_time_diff(drilldown['timestamp'])
            user['uploads'] = uploads
        elif not uploads:
            return RedirectResponse(url="/start-query")
        
        context = dict(request=request, user=user, cookies_confirmed=user.get('cookies_confirmed'))
        response = templates.TemplateResponse("query-feed.html", context=context)
        response.headers["Cache-Control"] = "no-store"
        return response
    
    response = templates.TemplateResponse("not-found.html", context=dict(request=request))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/my-profile")
async def my_profile(request: Request):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})

    if user:
        transactions = await app.mongodb['transactions'].find({"user_id": user_id}).to_list(length=1000)
        for transaction in transactions:
            transaction['amount']['amount'] = Decimal(str(transaction['amount']['amount']))
        balance = dict(
            amount=sum([transaction['amount']['amount'] for transaction in transactions]),
            currency='$'
        )
        response = templates.TemplateResponse("user-profile.html", context=dict(request=request, user=user, balance=balance, transactions=transactions))
        response.headers["Cache-Control"] = "no-store"
        return response
    
    response = templates.TemplateResponse("not-found.html", context=dict(request=request))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/add-credits/{amount}")
async def add_credits(request: Request, amount: str):
    user_id = get_user_id_from_request(request)
    user = await app.mongodb['users'].find_one({"user_id": user_id})

    if user:
        transaction_description = 'Credits received'
        amount = f"{float(amount):.2f}"
        await add_transaction(user_id=user_id, amount=Money(amount=Decimal128(amount), currency='$'), description=transaction_description)
        return RedirectResponse(url="/my-profile")
    
    return templates.TemplateResponse("not-found.html", context=dict(request=request))


## Cookies

@app.post("/cookies-confirm", response_class=JSONResponse)
async def cookies_confirm(request: Request, background_tasks: BackgroundTasks):
    # Confirm cookies in DB if user is logged in
    user_id = get_user_id_from_request(request)
    if user_id:
        user = await request.app.mongodb['users'].find_one({"user_id": user_id})
        if user:
            await request.app.mongodb['users'].update_one({"user_id": user_id}, {"$set": {"cookies_confirmed": True}})

    response = Response(status_code=status.HTTP_200_OK)
    new_cookies_token = create_cookies_confirmed_token(cookies_confirmed=True)
    response = set_token_to_browser(response, 'cookies', new_cookies_token)

    # Point browser to do not store cache
    response.headers["Cache-Control"] = "no-store"

    return response


## Info popup

@app.post("/info-popup-viewed", response_class=JSONResponse)
async def info_popup_viewed(request: Request):
    user_id = get_user_id_from_request(request)
    if user_id:
        await app.mongodb['users'].update_one({"user_id": user_id}, {"$set": {"info_popup_viewed_at": datetime.now(timezone.utc)}})
        return Response(status_code=status.HTTP_200_OK)
    return Response(status_code=status.HTTP_400_BAD_REQUEST)




## Document Retrieval API
#@app.post("/semantic-search/", methods=["POST"], response_class=JSONResponse)
#@app.api_route("/semantic-search/", methods=["POST"], response_class=JSONResponse)
@app.get("/semantic-search/", response_class=JSONResponse)
async def semantic_search(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(content={"error message": "Invalid JSON body"}, status_code=400)
    
    api_key = body.get("api_key")
    query_text = body.get("query_text")
    start_date = body.get("start_date", "2018-01-01")
    end_date = body.get("end_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    max_results = body.get("max_results", 10)
    score = body.get("score", 0.75)
    source_list = body.get("source", [])
    chunk_types = body.get("type", [])

    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse(content={"error message": "incorrect start_date param, needs to be YYYY-MM-DD"}, status_code=400)
    if end_date:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse(content={"error message": "incorrect end_date param, needs to be YYYY-MM-DD"}, status_code=400)

    if max_results < 1 or not isinstance(max_results, int):
        return JSONResponse(content={"error message": "incorrect limit param, needs to be an integer greater than 0"}, status_code=400)
        
    if score < 0 or score> 1 or not isinstance(score, float):
        return JSONResponse(content={"error message": "incorrect score param, needs to be a float between 0 and 1"}, status_code=400)
    

    user = await request.app.mongodb["users"].find_one({
        "$and": [
            {"$expr": {"$eq": [{"$arrayElemAt": ["$auth_links.auth_link", -1]}, api_key]}},
            {"auth_links": {"$elemMatch": {"auth_link": api_key, "access_token_assigned": False}}}
        ]
    })

    if user and query_text:
        user_id = user.get("user_id")
        try:
            query_embedding = await get_text_embedding(query_text)
            query_embedding = [query_embedding]
            params = {
                "mongodb": app.mongodb,
                "input_embeddings": query_embedding,
                "number_of_results": max_results,
                "min_similarity_score": score,
                "chart_min_similarity_score": score,
                "number_of_candidates": 3000
            }
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if source_list:            
                params["source_list"] = source_list
            if chunk_types:
                params["chunk_types"] = chunk_types
            relevant_results = await find_relevant_chunks_from_vectors(**params)

            for item in relevant_results:
                if 'published' in item and isinstance(item['published'], datetime):
                    item['published'] = item['published'].isoformat()
                item.pop('embedding', None)
                item.pop('last_modified', None)
                item.pop('external_origin', None)
                item.pop('card_background_colour', None)

            await request.app.mongodb["api_logs"].insert_one({
                "user_id": user_id,
                "query_text": query_text,
                "timestamp": datetime.now(timezone.utc),
                "parameters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "max_results": max_results,
                    "score": score,
                    "source_list": source_list,
                    "chunk_types": chunk_types
                }
            })
            return JSONResponse(content=relevant_results, status_code=200)
        except Exception as e:
            return JSONResponse(content={"error message": str(e)}, status_code=500)
    
    return JSONResponse(content={"error message": "incorrect API Syntax"}, status_code=400)

# @app.get("/semantic-search/", response_class=JSONResponse)
# async def semantic_search(api_key: str, 
#                           query_text: str,
#                           start_date: str = None,
#                           end_date: str = None,
#                           max_results: int = 10,
#                           score: float = 0.85):
    
#     if start_date:
#         try:
#             start_date = datetime.strptime(start_date, "%Y-%m-%d")
#         except ValueError:
#             return JSONResponse(content={"error message": "incorrect start_date param, needs to be YYYY-MM-DD"}, status_code=400)
#     if end_date:
#         try:
#             end_date = datetime.strptime(end_date, "%Y-%m-%d")
#         except ValueError:
#             return JSONResponse(content={"error message": "incorrect end_date param, needs to be YYYY-MM-DD"}, status_code=400)
            
#     if max_results < 1 or not isinstance(max_results, int):
#         return JSONResponse(content={"error message": "incorrect limit param, needs to be an integer greater than 0"}, status_code=400)
        
#     if score < 0 or score> 1 or not isinstance(score, float):
#         return JSONResponse(content={"error message": "incorrect score param, needs to be a float between 0 and 1"}, status_code=400)
    

#     user = await app.mongodb["users"].find_one({
#         "$and": [
#             {"$expr": {"$eq": [{"$arrayElemAt": ["$auth_links.auth_link", -1]}, api_key]}},
#             {"auth_links": {"$elemMatch": {"auth_link": api_key, "access_token_assigned": False}}}
#         ]
#     })

#     if user and query_text:
#         user_id = user.get("user_id")
#         try:
#             query_embedding = await get_text_embedding(query_text)
#             query_embedding = [query_embedding]
#             params = {
#                 "mongodb": app.mongodb,
#                 "input_embeddings": query_embedding,
#                 "number_of_results": max_results,
#                 "min_similarity_score": score
#             }
#             if start_date:
#                 params["start_date"] = start_date
#             if end_date:
#                 params["end_date"] = end_date
#             relevant_results = await find_relevant_chunks_from_vectors(**params)

#             for item in relevant_results:
#                 if 'published' in item and isinstance(item['published'], datetime):
#                     item['published'] = item['published'].isoformat()
#                 item.pop('embedding', None)
#                 item.pop('last_modified', None)
#                 item.pop('external_origin', None)
#                 item.pop('card_background_colour', None)
#             return JSONResponse(content=relevant_results, status_code=200)
#         except Exception as e:
#             return JSONResponse(content={"error message": str(e)}, status_code=500)
    
#     return JSONResponse(content={"error message": "incorrect API Syntax"}, status_code=400)

## Pitchdeck Tracking
# @app.get("/tracking-image/{image_name}", response_class=FileResponse)
# async def tracking_image(request: Request, image_name: str):
#     try:
#         await request.app.mongodb["pitchdeck_tracking"].insert_one({
#             "slide_page": image_name,
#             "accessed_at": datetime.now(timezone.utc)
#         })
#     except Exception as e:
#         pass
#     return FileResponse(f"static/media/images/logo.svg")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
