import os
import sys
current_dir= os.getcwd()
sys.path.append(current_dir)
from gradio import ChatMessage
import copy
import gradio as gr
import requests
import uuid
import pandas as pd
from config_URL import (
    API_VALIDATE_USER,
    API_CONV_START,
    API_CONV_SEND,
    API_GET_HISTORY,
    API_LOGOUT,
    API_CREATE_EMPTY_COLLECTION,
    API_INGEST_BATCH,
    auth_html,
)
from utils.utils_helper_func import (
    show_client,
    get_all_sessions,
    convert_chat,
    get_doc_names_frontend,
    get_batch_status_frontend,
    empty_batch_status_frame,
    feedback_logger,
)
from utils.utils_logging import logger, initialize_logging, FRONTEND_LOG

# logging config
initialize_logging(FRONTEND_LOG)

# Session state management
class SessionState:
    def __init__(self):
        self.authenticated = False
        self.session_id = ""
        self.username = ""
        self.read_collection = ""
        self.ingest_collection=""
        self.user_client = None
        self.existing_conversations=[]
        self.access_token = ""
        self.is_admin = False
        self.poll_active = False
        self.batch_status_df = empty_batch_status_frame()
        self.poll_grace_cycles = 0

    def auth_headers(self):
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

session_instances={}

# Gradio functions
def initialize_instance(request: gr.Request):
    """ Update global session variable dict with session hash id as the key for a user state for better downstream processing.
        Send data to frontend to display: Username, existing sessions dropdown, available documents to chat with

    Args:
        request (gr.Request): session request when user opens the frontend url

    Returns: Markdown with user name after login
    """
    session_state = session_instances.get(request.session_hash)
    if not session_state and request.username in session_instances:
        session_instances[request.session_hash] = session_instances.pop(request.username)
        session_state = session_instances[request.session_hash]

    if session_state:
        logger.info("Session id: %s initialised for user: %s", session_state.session_id, request.username)
        existing_choices = session_state.existing_conversations
        conv_id = session_state.session_id
        available_doc_markdown, admin_access, col_type = get_doc_names_frontend(
            conv_id=conv_id,
            username=request.username,
            headers=session_state.auth_headers(),
        )
        session_state.is_admin = admin_access
        if not admin_access:
            session_state.poll_active = False
            session_state.batch_status_df = empty_batch_status_frame()
            session_state.poll_grace_cycles = 0
        status_df = empty_batch_status_frame()
        status_visible = False
        if admin_access:
            try:
                status_df = get_batch_status_frontend(
                    conv_id=conv_id,
                    headers=session_state.auth_headers(),
                )
                session_state.batch_status_df = status_df
                has_active = not status_df.empty and any(
                    status in {"queued", "processing"} for status in status_df["Status"].tolist()
                )
                session_state.poll_active = has_active
                session_state.poll_grace_cycles = 12 if has_active else 0
                status_visible = not status_df.empty
            except Exception as err:
                logger.error("Unable to fetch batch status for %s: %s", request.username, str(err))
                session_state.batch_status_df = empty_batch_status_frame()
                session_state.poll_active = False
                session_state.poll_grace_cycles = 0
        ingestion_button_updated = gr.update(interactive=admin_access)
        status_component_update = gr.update(value=status_df, visible=status_visible)
        dropdown_update = gr.update(choices=existing_choices, value=None)
        doc_table_update = gr.update(value=available_doc_markdown)
        return (
            f"# KI-Pilot - AI Assistant (Mode: {col_type})<br>",
            f"# KI-Pilot - AI Assistant (Mode: {col_type})",
            dropdown_update,
            doc_table_update,
            ingestion_button_updated,
            status_component_update,
        )

    logger.warning(
        "initialize_instance called without active session for user %s (hash: %s)",
        request.username,
        request.session_hash,
    )
    placeholder_docs = pd.DataFrame(
        {"Document": ["Bitte melden Sie sich erneut an."], "Date of Creation": [""]}
    )
    return (
        "# KI-Pilot - AI Assistant",
        "# KI-Pilot - AI Assistant",
        gr.update(choices=[], value=None),
        gr.update(value=placeholder_docs),
        gr.update(interactive=False),
        gr.update(value=empty_batch_status_frame(), visible=False),
    )

def upload_files(filepaths, request: gr.Request):
    """Handle multi-file ingestion by queuing documents for batch processing."""
    session_state = session_instances.get(request.session_hash)
    if not session_state or not session_state.authenticated:
        warning = "Bitte zuerst authentifizieren."
        return (
            gr.update(interactive=False),
            gr.update(value=warning, visible=True),
            gr.update(),
            gr.update(value=empty_batch_status_frame(), visible=False),
        )
    if not session_state.is_admin:
        warning = "Batch-Upload erfordert Admin-Rechte."
        return (
            gr.update(interactive=False),
            gr.update(value=warning, visible=True),
            gr.update(),
            gr.update(value=empty_batch_status_frame(), visible=False),
        )

    files = filepaths or []
    if not isinstance(files, list):
        files = [files]

    file_list = []
    for file_obj in files:
        if file_obj is None:
            continue
        path = getattr(file_obj, "name", None) or str(file_obj)
        if path:
            file_list.append(path)

    if not file_list:
        info = "Keine gültigen Dateien ausgewählt."
        return (
            gr.update(interactive=session_state.is_admin),
            gr.update(value=info, visible=True),
            gr.update(),
            gr.update(value=empty_batch_status_frame(), visible=session_state.is_admin),
        )

    logger.info(
        "User %s queuing %s document(s) for collection %s",
        request.username,
        len(file_list),
        session_state.read_collection,
    )

    data = {
        "conv_id": session_state.session_id,
        "files": file_list,
        "ingest_collection": session_state.read_collection,
    }

    queued_message = ""
    session_state.poll_active = True
    session_state.poll_grace_cycles = 12
    try:
        response = requests.post(
            API_INGEST_BATCH.format(
                session_id_user=f"{session_state.session_id}${session_state.username}"
            ),
            json=data,
            headers=session_state.auth_headers(),
        )
        response.raise_for_status()
        queued_jobs = response.json().get("queued_jobs", [])
        if queued_jobs:
            names = ", ".join(job.get("filename", "") for job in queued_jobs)
            queued_message = f"{len(queued_jobs)} Dokument(e) in die Warteschlange gestellt: {names}"
        else:
            queued_message = "Keine Dokumente zur Warteschlange hinzugefügt."
    except Exception as exc:
        logger.error(
            "Fehler beim Batch-Upload für Session %s: %s",
            session_state.session_id,
            str(exc),
        )
        queued_message = f"Batch-Upload fehlgeschlagen: {str(exc)}"
        session_state.poll_active = False
        session_state.batch_status_df = empty_batch_status_frame()
        session_state.poll_grace_cycles = 0

    available_doc_markdown, admin_access, _ = get_doc_names_frontend(
        conv_id=session_state.session_id,
        username=request.username,
        headers=session_state.auth_headers(),
    )
    session_state.is_admin = admin_access

    status_df = empty_batch_status_frame()
    if session_state.is_admin and session_state.poll_active:
        try:
            status_df = get_batch_status_frontend(
                conv_id=session_state.session_id,
                headers=session_state.auth_headers(),
            )
            session_state.batch_status_df = status_df
            has_active = not status_df.empty and any(
                status in {"queued", "processing"} for status in status_df["Status"].tolist()
            )
            if has_active:
                session_state.poll_active = True
                session_state.poll_grace_cycles = 12
            elif session_state.poll_grace_cycles > 0:
                session_state.poll_active = True
            else:
                session_state.poll_active = False
                session_state.poll_grace_cycles = 0
        except Exception as err:
            logger.error(
                "Statusabfrage nach Batch-Upload fehlgeschlagen für %s: %s",
                session_state.session_id,
                str(err),
            )
            session_state.poll_active = False
            session_state.batch_status_df = empty_batch_status_frame()
            session_state.poll_grace_cycles = 0

    status_visible = session_state.is_admin and not session_state.batch_status_df.empty
    status_df = session_state.batch_status_df if status_visible else empty_batch_status_frame()
    return (
        gr.update(interactive=session_state.is_admin),
        gr.update(value=queued_message, visible=True),
        gr.update(value=available_doc_markdown),
        gr.update(value=status_df, visible=status_visible),
    )

def send_chat(message, request: gr.Request):
    """ Send user message to chat api and get response

    Args:
        message (str): user_message
        request (gr.Request): requests from user session

    Returns:
        reply: reply from chatbot
    """
    session_state = session_instances.get(request.session_hash)
    if not session_state or not session_state.authenticated:
        return "Please authenticate first."
    data = {"conv_id": session_state.session_id, "message": message}
    try:
        response = requests.post(
            API_CONV_SEND.format(
                session_id_user=f"{session_state.session_id}${session_state.username}"
            ),
            json=data,
            headers=session_state.auth_headers(),
        )
        response.raise_for_status()
        reply = str(response.json())
        logger.info(
            "Bot response successful for user: %s for session id: %s",
            session_state.username,
            session_state.session_id,
        )
        return reply
    except Exception as e:
        logger.error(
            "Got an error during getting bot response for session id: %s: %s",
            session_state.session_id,
            str(e),
        )
        return f"Chat error: {str(e)}"

def respond(message, chat_history, request: gr.Request):
        if message:
            response= send_chat(message, request=request)
        else:
            response= "What can I help you with?"
        chat_history.append(ChatMessage(role="user", content=message))
        chat_history.append(ChatMessage(role="assistant", content=response))
        return "",chat_history

def handle_feedback(like_data: gr.LikeData, request:gr.Request):
    """Handle like/dislike events and show feedback input for dislikes"""
    session_state = session_instances[request.session_hash]
    conv_id = session_state.session_id
    username = session_state.username
    if not like_data.liked:  # If disliked
        return gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), like_data.value[0]
    else:  # If liked
        feedback_response = feedback_logger(
            conv_id=conv_id,
            username=username,
            LLM_response=like_data.value[0],
            feedback="Positive",
            feedback_comment="N/A",
            headers=session_state.auth_headers(),
        )
        if not feedback_response:
            logger.error("Feedback not logged for user %s in session: %s", username, conv_id)
        else: 
            gr.Info("Thank you for your feedback!")
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), like_data.value[0]
    
def submit_feedback(feedback_text, message_content, request:gr.Request):
    session_state = session_instances[request.session_hash]
    conv_id = session_state.session_id
    username = session_state.username
    """Process the feedback submitted by user"""
    if feedback_text.strip():
        feedback_response = feedback_logger(
            conv_id=conv_id,
            username=username,
            LLM_response=message_content,
            feedback="Negative",
            feedback_comment=feedback_text,
            headers=session_state.auth_headers(),
        )
        print(f"Feedback received for message '{message_content}': {feedback_text}")
        if not feedback_response: 
            logger.error("Feedback not logged for user %s in session: %s", username, conv_id)
        else: 
            logger.info("Feedback: %s submitted for user %s, session: %s", feedback_text, username, conv_id)
            gr.Info("Thank you for your feedback!")
    return "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)


def refresh_batch_status(request: gr.Request):
    """Poll backend for updated batch ingestion status."""
    session_state = session_instances.get(request.session_hash)
    if not session_state or not session_state.authenticated or not session_state.is_admin:
        return gr.update(value=empty_batch_status_frame(), visible=False)

    if not session_state.poll_active:
        visibility = session_state.is_admin and not session_state.batch_status_df.empty
        return gr.update(value=session_state.batch_status_df, visible=visibility)

    try:
        status_df = get_batch_status_frontend(
            conv_id=session_state.session_id,
            headers=session_state.auth_headers(),
        )
        session_state.batch_status_df = status_df
        active = not status_df.empty and any(
            status in {"queued", "processing"} for status in status_df["Status"].tolist()
        )
        if active:
            session_state.poll_active = True
            session_state.poll_grace_cycles = 12
        else:
            if session_state.poll_grace_cycles > 0:
                session_state.poll_grace_cycles -= 1
                session_state.poll_active = True
            else:
                session_state.poll_active = False
        visibility = active or not status_df.empty
        return gr.update(value=status_df, visible=visibility)
    except Exception as err:
        logger.error(
            "Fehler beim Aktualisieren des Batch-Status für %s: %s",
            session_state.session_id,
            str(err),
        )
        session_state.poll_active = False
        session_state.poll_grace_cycles = 0
        session_state.batch_status_df = empty_batch_status_frame()
        return gr.update(value=session_state.batch_status_df, visible=False)

def dropdown_update_convo(dropdown, evt: gr.SelectData, request: gr.Request):
    """ Function that gets triggered when user selects conv from drop down. It gets conversation history of selected session and updates session id to selected session for
        both frontend and backend states. Then it converts the chat element to gradio chat element and updates the window in frontend.

    Args:
        dropdown (_type_): dropdown function
        evt (gr.SelectData): Has the selected conv id value
        request (gr.Request): network variables containing username

    Returns:
        chatbot_selected: chat history of selected conv id
    """
    session_state = session_instances[request.session_hash]
    data = {
        "old_conv_id": session_state.session_id,
        "new_conv_id": str(evt.value),
        "username": request.username,
    }
    response = requests.post(
        API_GET_HISTORY.format(session_id_user=str(evt.value) + "$" + request.username),
        json=data,
        headers=session_state.auth_headers(),
    )
    response.raise_for_status()
    session_state.session_id = str(evt.value)
    session_state.poll_active = True
    session_state.poll_grace_cycles = 12
    session_state.batch_status_df = empty_batch_status_frame()
    logger.info("User %s changed chat session to previous session: %s", request.username, evt.value)
    chatbot_selected = gr.Chatbot(value=convert_chat(response.json()),type="messages", placeholder="Hi, how can I help you today?", scale=9, resizable=True, show_copy_button=True, height=500)
    return chatbot_selected

def authenticate_user(username: str, password: str):
    """ First validates authentication and then populates the temporary session varibales to init the backend for user. 
        Finally adds user state object to global dict

    Args:
        username (str): username
        password (str): password

    Returns:
        bool: Whether succesfully authenticated or not
    """
    data = {"username": username, "password": password}
    try:
        logger.info("Logging in for: %s", username)
        response = requests.post(API_VALIDATE_USER.format(user=username), json=data)
        if response.status_code == 401:
            logger.info("Invalid credentials for %s", username)
            return False
        response.raise_for_status()
        token_payload = response.json()
        access_token = token_payload.get("access_token")
        if access_token:
            temp_state=SessionState()
            temp_state.authenticated = True
            temp_state.username = username
            temp_state.session_id = str(uuid.uuid4())
            temp_state.user_client = show_client(username=username, password=password)
            temp_state.access_token = access_token
            token_type = token_payload.get("token_type", "bearer")
            if token_type.lower() != "bearer":
                logger.warning("Unexpected token type %s for user %s", token_type, username)
            collections = temp_state.user_client.list_collections()
            init_data = {
                "conv_id": temp_state.session_id,
                "username": temp_state.username,
                "password": password
            }
            init_response = requests.post(
                API_CONV_START,
                json=init_data,
                headers=temp_state.auth_headers(),
            )
            init_response.raise_for_status()
            logger.info("User %s has collection: %s assigned at the backend", username, init_response.json()["user_collection"])
            temp_state.read_collection= init_response.json()["user_collection"]
            # create collection if not present
            if temp_state.read_collection not in collections:
                logger.warning("No collections exist for user: %s, creating collection %s", username, temp_state.read_collection)
                collection_response = requests.post(
                    API_CREATE_EMPTY_COLLECTION.format(collection_name=temp_state.read_collection),
                    headers=temp_state.auth_headers(),
                )
                collection_response.raise_for_status()
                if not collection_response.json():
                    return False
            temp_state.existing_conversations = get_all_sessions(
                username=username,
                new_conv_id=copy.deepcopy(temp_state.session_id),
                headers=temp_state.auth_headers(),
            )
            session_instances[username]=copy.deepcopy(temp_state)
            logger.info("Current object created for %s has existing convos: %s", username, temp_state.existing_conversations)
            logger.info("Successful authentication for %s, session id: %s", username, temp_state.session_id)
            return True
        else:
            logger.info("Unsuccessful authentication for %s",username)
            return False
    except Exception as e:
        logger.error("Got an error during authentication: %s", str(e))
        return False

def do_quit(request: gr.Request):
        """Exit the chat
        """
        session_state = session_instances[request.session_hash]
        data = {
            "conv_id": session_state.session_id,
            "user": request.username,
        }
        response = requests.post(
            API_LOGOUT,
            json=data,
            headers=session_state.auth_headers(),
        )
        if response.status_code==200:
            logger.info("%s for user %s", response.json(), request.username)
        else:
            logger.error("Error occurred: %s", response.json())
            raise Exception("Error while logging out")


def cleanup_instance(request: gr.Request):
    if request.session_hash in session_instances:
        logger.info("User %s logged out", request.username)
        del session_instances[request.session_hash]
        logger.debug("Current global session cache: %s", session_instances.keys())

""" Gradio Interface Setup using Blocks API (for flexibility) """
with gr.Blocks() as chat:
    chatbot = gr.Chatbot(type="messages", placeholder="Hi, how can I help you today?", scale=15, resizable=True, show_copy_button=True, height=600, container=False, sanitize_html=False, feedback_options=("Like", "Dislike"))
    msg = gr.Textbox(type="text", placeholder="Type your question here...", label="User Message", submit_btn=True, scale=15)
    clear = gr.ClearButton([msg, chatbot], size="sm")
    last_message = gr.State("")
    msg.submit(respond, [msg, chatbot], [msg, chatbot], trigger_mode="once")
    with gr.Row():
        feedback_input = gr.Textbox(
            placeholder="What went wrong? Your feedback would be crucial in improving the system.", 
            label="Feedback", visible=False, lines=3, autofocus=True, autoscroll=True
            )
    with gr.Row():
        submit_feedback_btn = gr.Button("Submit Feedback", visible=False, variant="primary")
        cancel_feedback_btn = gr.Button("Cancel", visible=False)

with gr.Blocks(fill_width=True) as demo:
    with gr.Tab("Chat_Session"):
        m= gr.Markdown("# KI-Pilot - AI Assistant")
        conversation_list=[]
        chat.render()
        with gr.Sidebar(position="left", width=360, open=False):
            gr.Markdown("### Widgets")
            select_conversation = gr.Dropdown(
                choices=conversation_list, 
                label="Select Conversation",
                value=None
            )
            gr.HTML("<div style='flex-grow: 1;'></div>")
            logout_button_front = gr.Button("Logout", size="sm")
    with gr.Tab("Ingested Documents (RAG)"):
        doc_markdown= gr.Markdown("# KI-Pilot - AI Assistant")
        db= gr.Dataframe()
        batch_status_table = gr.Dataframe(
            value=empty_batch_status_frame(),
            label="Batch Upload Status",
            interactive=False,
            visible=False,
        )
        ingestion_button = gr.UploadButton(
            label="Ingest Documents",
            size="md",
            variant="primary",
            file_types=["file"],
            file_count="multiple",
            interactive=True,
        )
        gr.Markdown("Note: Only PDFs < 50 MB are supported!")
        result= gr.Markdown(visible=False)
        with gr.Sidebar(position="left", width=360, open=False):
            gr.Markdown("### Widgets")
            logout_button_back = gr.Button("Logout", size="sm")
    status_timer = gr.Timer(value=5.0)
    demo.load(
        initialize_instance,
        None,
        [m, doc_markdown, select_conversation, db, ingestion_button, batch_status_table],
        concurrency_limit=20,
    )

    chatbot.like(handle_feedback, 
        None, 
        [feedback_input, submit_feedback_btn, cancel_feedback_btn, msg, clear, last_message])
    
    submit_feedback_btn.click(
        submit_feedback,
        [feedback_input, last_message],
        [feedback_input, feedback_input, submit_feedback_btn, cancel_feedback_btn, msg, clear]
    )

    cancel_feedback_btn.click(
        lambda: ("", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
                  gr.update(visible=True), gr.update(visible=True)),
        None,
        [feedback_input, feedback_input, submit_feedback_btn, cancel_feedback_btn, 
         msg, clear]
    )

    ingestion_button.upload(
        fn=lambda x: gr.update(interactive=False),
        inputs=ingestion_button,
        outputs=ingestion_button,
    ).then(
        fn=upload_files,
        inputs=ingestion_button,
        outputs=[ingestion_button, result, db, batch_status_table],
        trigger_mode="once",
        show_progress="full",
        show_progress_on=[ingestion_button, result, db, batch_status_table],
    )

    logout_button_front.click(do_quit, inputs=None, outputs=None).then(fn=None, inputs=None, outputs=None, js="() => { window.location.href = '/logout'; }")
    logout_button_back.click(do_quit, inputs=None, outputs=None).then(fn=None, inputs=None, outputs=None, js="() => { window.location.href = '/logout'; }")
    select_conversation.select(dropdown_update_convo, select_conversation, [chatbot]).then(
        refresh_batch_status,
        None,
        batch_status_table,
    )
    status_timer.tick(refresh_batch_status, None, batch_status_table)
    demo.unload(cleanup_instance)

demo.launch(share=False, auth=authenticate_user, auth_message=auth_html, show_error=True, server_name="0.0.0.0", server_port=8083)
