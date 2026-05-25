# Virtual Twin Project Requirements

## 1. Project Overview

**Virtual Twin** is a standalone AI backend system designed to power the chatbot on Mohamad Hanafi’s portfolio website.

The chatbot will act as a professional digital representative of Mohamad. It will answer questions about his background, skills, services, projects, experience, and qualifications. It will also guide users through the portfolio website and handle contact requests conversationally, without using a traditional contact form.

The frontend portfolio has already been built using **Next.js**. This project focuses on building the backend using **Python, FastAPI, Hugging Face Transformers, and a locally hosted Qwen model**.

---

## 2. Main Goal

The goal is to build an AI-powered virtual assistant that can:

1. Answer questions about Mohamad using a RAG-based knowledge base.
2. Explain what Mohamad can do and how he can help potential clients, collaborators, or employers.
3. Navigate users to relevant pages or sections in the portfolio.
4. Replace the traditional contact form with a chatbot-based contact flow.
5. Later support meeting scheduling through Google Calendar.

---

## 3. Core Concept

The chatbot should function as a **Virtual Twin**.

This means it should represent Mohamad professionally and respond as a knowledgeable assistant that understands his:

- Engineering background
- AI and software development skills
- Portfolio projects
- Services
- Research experience
- Innovation interests
- Qualifications and certificates
- Professional value proposition

The chatbot should not pretend to be Mohamad personally. It should behave as an AI representative of Mohamad.

Example positioning:

> “I am Mohamad’s virtual assistant. I can explain his work, projects, services, and help you contact him.”

---

## 4. Technology Stack

### 4.1 Frontend

The frontend already exists and is built with:

- Next.js
- React
- Portfolio chatbot interface

The frontend will communicate with the backend through HTTP API requests.

### 4.2 Backend

The backend will be built as a separate project using:

- Python
- FastAPI
- Hugging Face Transformers
- Qwen/Qwen3-4B
- MLX LoRA fine-tuning stack for Apple Silicon
- Uvicorn for local development

### 4.3 LLM Model

The first selected model is:

- **Qwen/Qwen3-4B**

Reason for choosing this model:

- Open-weight model available through Hugging Face
- Strong balance between quality and local Apple Silicon development cost
- Suitable for chat, reasoning, coding, and multilingual use
- Supports LoRA fine-tuning workflows through MLX
- Can be served locally on a Mac or deployed later with a model-serving backend

The model should be fine-tuned using **MLX LoRA** first, rather than full fine-tuning, to reduce memory requirements on Apple Silicon.

### 4.4 Deployment

The backend can initially run locally on Apple Silicon. Later deployment options include:

- A Mac-based local or hosted machine
- Hugging Face Spaces or Inference Endpoints
- RunPod, Modal, Lambda Labs, or similar infrastructure if moving to CUDA/cloud training later
- Google Cloud Run only if using an external model server or a CPU-compatible lightweight inference path

The backend should still be designed to be container-ready using Docker, but local model inference and fine-tuning require hardware planning.

### 4.5 Future Database / RAG Storage

Possible options for RAG storage:

- Supabase pgvector
- Qdrant
- Chroma
- Google Cloud-compatible vector storage

For the first version, the exact vector database can be decided later. The backend should be designed so the RAG layer can be added without rewriting the whole API.

---

## 5. System Architecture

The planned architecture is:

```txt
Next.js Portfolio Frontend
        ↓
FastAPI Virtual Twin Backend
        ↓
Model Service / Inference Layer
        ↓
Qwen/Qwen3-4B local model
        ↓
RAG Knowledge Base
        ↓
Actions / Tools
```

The backend should return both text responses and structured actions when needed.

Example response:

```json
{
  "reply": "Sure, I’ll show you Mohamad’s projects.",
  "action": {
    "type": "navigate",
    "target": "/projects"
  }
}
```

The backend does not directly control the browser. It sends an action to the frontend, and the frontend performs the navigation.

---

## 6. Main Features

## 6.1 Chatbot Conversation

The backend must provide a chat endpoint that receives user messages and returns chatbot responses.

Required endpoint:

```txt
POST /chat
```

The endpoint should accept:

- Current user message
- Conversation history
- Optional mode, such as normal chat or contact mode

Example request:

```json
{
  "message": "What kind of apps can Mohamad build?",
  "history": [],
  "mode": "chat"
}
```

Example response:

```json
{
  "reply": "Mohamad can build AI-powered web applications, RAG systems, chatbot interfaces, automation tools, and clean portfolio or business websites.",
  "action": null
}
```

---

## 6.2 RAG-Based Knowledge Answering

The chatbot should use Retrieval-Augmented Generation to answer questions about Mohamad.

The RAG knowledge base should include:

- About section
- CV content
- Project descriptions
- Services
- Skills
- Certificates
- AI development experience
- Engineering innovation background
- Publications or research highlights, if needed
- Frequently asked questions

The chatbot should retrieve relevant context before answering.

The chatbot must avoid inventing information. If the answer is not available in the knowledge base, it should say that Mohamad can follow up.

Example:

User:

> “Does Mohamad have experience with RAG systems?”

Expected behavior:

1. Retrieve relevant content about Mohamad’s AI/RAG experience.
2. Generate a concise and professional answer.
3. Avoid unsupported claims.

---

## 6.3 Website Navigation Agent

The chatbot should be able to guide users through the portfolio.

Example user messages:

- “Show me his projects.”
- “Where can I see his AI work?”
- “Take me to his services.”
- “I want to know more about his experience.”

The backend should return a structured navigation action.

Example:

```json
{
  "reply": "Sure, I’ll take you to the services section.",
  "action": {
    "type": "navigate",
    "target": "/services"
  }
}
```

The frontend will handle the actual navigation.

Possible navigation targets:

```txt
/
/about
/projects
/services
/experience
/publications
/contact
```

If the portfolio is a single-page website, the target can be a section ID instead:

```txt
#about
#projects
#services
#experience
#contact
```

---

## 6.4 Chatbot-Based Contact Flow

There will be no traditional contact form on the portfolio website.

When a user clicks the **Get in Touch** button, the chatbot should open and start a structured contact flow.

The chatbot should ask for:

1. User’s name
2. User’s email address
3. User’s message or reason for contact
4. Confirmation before submission

Example flow:

```txt
User clicks “Get in Touch”
        ↓
Bot: Sure, I can help you contact Mohamad. What is your name?
        ↓
User: John Smith
        ↓
Bot: Thanks John. What is your email address?
        ↓
User: john@example.com
        ↓
Bot: What message would you like to send to Mohamad?
        ↓
User: I am interested in building an AI chatbot for my company.
        ↓
Bot: Please confirm: your name is John Smith, your email is john@example.com, and your message is...
        ↓
User: Yes
        ↓
Bot: Thank you. I have sent your message to Mohamad.
```

The contact flow should be handled using a controlled state machine, not only free LLM conversation.

Suggested states:

```txt
idle
asking_name
asking_email
asking_message
confirming
submitted
cancelled
```

The backend should validate the email address before submission.

The backend should send the contact message to Mohamad by email.

Future option:

- Save leads to a database.

---

## 6.5 Email Sending

The backend should be able to send contact inquiries to Mohamad.

Possible email providers:

- Resend
- SendGrid
- Gmail SMTP
- Google Cloud email-compatible service

Recommended MVP option:

- Resend or SendGrid

Email content should include:

```txt
New portfolio inquiry

Name: [visitor name]
Email: [visitor email]
Message: [visitor message]
Source: Portfolio chatbot
```

The system should only send the email after the visitor confirms the collected information.

---

## 6.6 Future Google Calendar Booking

In a later phase, the chatbot should support meeting scheduling.

Possible flow:

```txt
User: I want to book a meeting with Mohamad.
Bot: Sure. What is your name and email?
Bot: What is the purpose of the meeting?
Bot: Here are available time slots.
User selects a slot.
Bot confirms.
Backend creates Google Calendar event.
```

The Google Calendar feature should not be included in the first MVP unless the basic chatbot, RAG, navigation, and contact flow are already working.

Future requirements:

- Google Calendar API integration
- OAuth or service-account strategy
- Time zone handling
- Availability checking
- Event creation
- Confirmation email

---

## 7. Backend API Requirements

### 7.1 Health Endpoint

```txt
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

### 7.2 Root Endpoint

```txt
GET /
```

Response:

```json
{
  "status": "ok",
  "message": "Virtual Twin API is running"
}
```

### 7.3 Chat Endpoint

```txt
POST /chat
```

Responsibilities:

- Receive user message
- Receive chat history
- Identify intent
- Retrieve RAG context when needed
- Generate answer using the local Qwen/Qwen3-4B model
- Return normal text response or structured action

### 7.4 Contact Endpoint or Contact Mode

The contact flow can be handled in one of two ways:

Option A:

```txt
POST /chat
```

With contact mode included in the request.

Option B:

```txt
POST /contact
```

With a dedicated endpoint for contact flow.

Recommended first version:

- Use `/chat` with a `mode` field.

Example:

```json
{
  "message": "start",
  "mode": "contact",
  "history": []
}
```

---

## 8. Project Folder Structure

Recommended backend structure:

```txt
virtual-twin/
  app/
    __init__.py
    main.py
    config.py

    routes/
      __init__.py
      chat.py
      health.py

    services/
      __init__.py
      llm.py
      rag.py
      contact_flow.py
      email_service.py
      tools.py

    schemas/
      __init__.py
      chat.py
      contact.py
      actions.py

    prompts/
      __init__.py
      system_prompt.py

  scripts/
    ingest.py

  content/
    about.md
    projects.md
    services.md
    cv.md
    faq.md

  tests/
    test_chat.py
    test_contact_flow.py

  .env
  .gitignore
  requirements.txt
  Dockerfile
  README.md
```

---

## 9. Environment Variables

Required for MVP:

```env
LLM_MODEL=Qwen/Qwen3-4B
HF_TOKEN=your_huggingface_token_if_needed
FRONTEND_URL=http://localhost:3000
```

Future variables:

```env
LOCAL_MODEL_PATH=
LORA_ADAPTER_PATH=
VECTOR_DB_URL=
VECTOR_DB_API_KEY=
RESEND_API_KEY=
CONTACT_RECEIVER_EMAIL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALENDAR_ID=
```

For production deployment, these values should be stored securely using environment variables or the secret manager provided by the chosen platform.

---

## 10. CORS Requirements

The backend must allow requests from the portfolio frontend.

Local frontend:

```txt
http://localhost:3000
```

Production frontend:

```txt
https://your-portfolio-domain.com
```

CORS should not be left fully open in production.

---

## 11. Prompt Requirements

The system prompt should define the chatbot as Mohamad’s virtual assistant.

The chatbot should:

- Be professional
- Be concise
- Be helpful
- Use clear language
- Explain Mohamad’s skills and services effectively
- Avoid unsupported claims
- Ask follow-up questions when needed
- Start the contact flow when the user wants to contact Mohamad
- Return structured actions when navigation is needed

The chatbot should not:

- Pretend to be Mohamad directly
- Invent experience or projects
- Make promises on Mohamad’s behalf
- Send contact emails without confirmation
- Book meetings without confirmation

---

## 12. RAG Requirements

The RAG system should eventually support:

1. Loading documents from the `content/` folder.
2. Splitting documents into chunks.
3. Creating embeddings.
4. Storing embeddings in a vector database.
5. Retrieving relevant chunks for each user question.
6. Passing retrieved context to the local Qwen model.
7. Returning grounded answers.

Initial content files:

```txt
content/about.md
content/projects.md
content/services.md
content/cv.md
content/faq.md
```

Each chunk should include metadata such as:

```txt
source
section
title
updated_at
```

The answer should be based on retrieved context when the question is about Mohamad.

---

## 13. Agent / Tool Requirements

The backend should support structured actions.

Initial actions:

```txt
navigate
start_contact_flow
submit_contact_message
```

Future actions:

```txt
check_calendar_availability
create_calendar_event
save_lead
```

Example action response:

```json
{
  "reply": "Sure, I’ll open the projects section.",
  "action": {
    "type": "navigate",
    "target": "#projects"
  }
}
```

---

## 14. Local Model and Deployment Requirements

The backend should support local development with a Hugging Face model.

Local model requirements:

- Use `Qwen/Qwen3-4B` as the base model.
- Use MLX LoRA for the first fine-tuning workflow on Apple Silicon.
- Keep fine-tuned LoRA adapters separate from the base model unless a merged export is needed.
- Do not commit model weights, checkpoints, or adapter output folders to Git.
- Store model path and adapter path in environment variables.
- Use a small test prompt to verify inference before connecting the frontend.

Deployment requirements:

- FastAPI app must run on host `0.0.0.0`
- App must use the port provided by the `PORT` environment variable
- Dockerfile should install dependencies from `requirements.txt`
- Secrets should not be hardcoded
- Environment variables should be configured in the deployment platform
- Health endpoint should be available
- A dedicated model-serving process should be considered if the model is too heavy to serve inside the FastAPI process

The production command should be compatible with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 15. Development Phases

### Phase 1: Basic FastAPI Backend

Build:

- Project structure
- `/health` endpoint
- `/chat` endpoint
- Local Qwen model loading or model-service connection
- Basic chatbot response
- CORS setup

### Phase 2: Frontend Connection

Connect the existing Next.js chatbot interface to the FastAPI backend.

Build:

- API fetch from frontend
- Display chatbot reply
- Send conversation history
- Handle loading states
- Handle backend errors

### Phase 3: Navigation Actions

Build:

- Intent detection for portfolio navigation
- Structured action response
- Frontend action handler
- Navigation to pages or sections

### Phase 4: Contact Flow

Build:

- Contact state machine
- Name collection
- Email collection
- Message collection
- Confirmation step
- Email validation
- Email sending

### Phase 5: RAG Knowledge Base

Build:

- Content files
- Ingestion script
- Embeddings
- Vector database integration
- Retrieval function
- Context-aware answers

### Phase 6: Local Fine-Tuning

Build:

- Training dataset in chat format
- MLX LoRA fine-tuning script
- Adapter checkpoint output
- Evaluation prompts
- Local inference using the fine-tuned adapter

### Phase 7: Deployment

Build:

- Dockerfile
- Deployment target selection
- Environment variables
- Secret management
- Production CORS
- Logging and monitoring
- External model-serving strategy if needed

### Phase 8: Google Calendar Integration

Build later:

- Availability checking
- Meeting request flow
- Calendar event creation
- Time zone handling
- Confirmation messages

---

## 16. MVP Scope

The first working MVP should include:

- FastAPI backend
- Local Qwen/Qwen3-4B model path or placeholder service
- `/chat` endpoint
- Basic virtual twin behavior
- Simple navigation action responses
- Basic contact flow start
- Local frontend-backend connection

The MVP does not need to include:

- Full RAG system
- Calendar booking
- Database lead storage
- Advanced analytics
- Admin dashboard

---

## 17. Success Criteria

The MVP is successful when:

1. The Next.js chatbot can send messages to FastAPI.
2. FastAPI can call the local Qwen model or a local model-serving process.
3. The chatbot can respond professionally about Mohamad.
4. The backend can return structured navigation actions.
5. The chatbot can start a contact flow when the user clicks “Get in Touch”.
6. The backend can be prepared for a realistic deployment path.

The full version is successful when:

1. The chatbot answers accurately using RAG.
2. The chatbot can guide users through the portfolio.
3. The chatbot can collect and send contact inquiries.
4. The chatbot can later help schedule meetings.
5. The system runs reliably on the chosen deployment platform.

---

## 18. Key Design Principle

The project should be built step by step.

Do not start with the most complex agent architecture. First build a reliable API, then add intelligence layer by layer.

Recommended order:

```txt
FastAPI API
→ local Qwen connection
→ frontend connection
→ navigation actions
→ contact flow
→ RAG
→ MLX LoRA fine-tuning
→ deployment
→ Google Calendar integration
```

This keeps the project clean, testable, and easy to improve.
