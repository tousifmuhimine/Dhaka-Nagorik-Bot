# 🏛️ Dhaka Nagorik Bot - Comprehensive Project Review

**Project Name:** Dhaka Civic Complaints Management System (Dhaka Nagorik Bot)  
**Version:** Phase 2 Complete  
**Status:** Production-Ready (Features), Development (Testing)  
**Last Updated:** April 17, 2026

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [Technology Stack](#technology-stack)
4. [Architecture & System Design](#architecture--system-design)
5. [Core Features](#core-features)
6. [AI/ML Models & Services](#aiml-models--services)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Setup & Installation](#setup--installation)
10. [Deployment Options](#deployment-options)
11. [File Structure](#file-structure)
12. [Configuration Reference](#configuration-reference)

---

## Executive Summary

**Dhaka Nagorik Bot** is a professional Django-based civic complaints management platform designed for Dhaka citizens, authorities, and administrators. The system uses cutting-edge AI/ML technology to intelligently extract complaint information, validate against policies, and route complaints to appropriate municipal authorities.

### Key Highlights:
- 🤖 **AI-Powered Chatbot** using Groq's Mixtral-8x7b model
- 🔍 **Vision Analysis** using Groq's Llama-4 Scout for image recognition
- 🌐 **Web Search Integration** via Tavily for fact-checking
- 📚 **RAG (Retrieval-Augmented Generation)** with ChromaDB for policy context
- 📄 **Automatic Document Generation** (PDF & DOCX)
- 📧 **Email Notifications** for authorities and citizens
- 🗄️ **Multi-Storage Support** (Local filesystem & Supabase Storage)
- 🔐 **Role-Based Access Control** (Citizens, Authorities, Admins)

---

## Project Overview

### Purpose

Dhaka Nagorik Bot simplifies the civic complaint filing process by:

1. **Intelligent Extraction**: AI extracts complaint details (category, location, duration) from natural conversations in Bangla or English
2. **Policy Validation**: Compares complaints against municipal policies using vector search
3. **Fact-Checking**: Validates complaint claims against web data to detect inconsistencies
4. **Automatic Routing**: Routes complaints to the appropriate municipal authority based on location
5. **Document Generation**: Creates formal complaint applications in PDF and DOCX format
6. **Status Tracking**: Citizens and authorities can track complaint progress in real-time
7. **Multi-Role Dashboard**: Separate interfaces for citizens, authorities, and administrators

### User Personas

| Role | Responsibilities | Features |
|------|-----------------|----------|
| **Citizen** | File and track complaints | Chat with bot, file complaints, download documents, track status |
| **Authority** | Review and resolve complaints | View thana-specific complaints, update status, add responses |
| **Admin** | System oversight | View all complaints, search/filter, manage users, generate reports |

---

## Technology Stack

### Backend Framework & Core

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | Django | 6.0.4 | Web application framework |
| **Python** | Python | 3.9+ | Programming language |
| **Database** | SQLite/PostgreSQL | Latest | Primary data storage |
| **Environment** | python-dotenv | 1.0.1 | Configuration management |

### AI/ML Services

| Service | Provider | Model | Purpose |
|---------|----------|-------|---------|
| **LLM Chat** | Groq | `mixtral-8x7b-32768` | Conversational AI & complaint extraction |
| **Vision Analysis** | Groq | `meta-llama/llama-4-scout-17b-16e-instruct` | Image analysis for complaint photos |
| **Embeddings** | SentenceTransformers | `paraphrase-multilingual-MiniLM-L12-v2` | Text embeddings for vector search (384-dimensional vectors) |
| **Web Search** | Tavily | Web Search API | Fact-checking and policy validation |
| **Vector Database** | ChromaDB (Local) | 0.5.0 | Local vector storage for policies and complaints |
| **Vector Database** | Supabase | pgvector | Optional hosted vector database |

### Document Generation

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| **PDF Generation** | ReportLab | 4.2.5 | Professional PDF document creation |
| **DOCX Generation** | python-docx | 1.1.2 | Microsoft Word document generation |
| **PDF Parsing** | PyPDF2 | 3.0.1 | Policy document parsing for indexing |

### Communications

| Component | Provider | Purpose |
|-----------|----------|---------|
| **Email Service** | SMTP | Sending complaint confirmations and notifications |
| **API Keys** | Environment Variables | Secure credential management |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Templates** | Django Templates + HTML | Server-side rendering |
| **Styling** | TailwindCSS | Responsive UI design |
| **JavaScript** | Vanilla JS/Fetch API | Frontend interactivity |
| **Chat UI** | Custom HTML/CSS | Modern chat interface with sidebar |
| **Desktop App** | Flet | Cross-platform desktop alternative (partial) |

### Utilities & Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| NLTK | 3.8.1 | Text processing and tokenization |
| email-validator | 2.1.0 | Email validation |
| requests | 2.31.0 | HTTP requests |
| numpy | 1.26.4 | Numerical computing (embeddings) |
| Groq SDK | 0.10.0 | Groq API client |
| Supabase SDK | 2.4.5 | Supabase client |
| LangChain | 1.2.15 | LLM orchestration |

---

## Architecture & System Design

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      END USERS                                  │
├──────────────────┬───────────────────┬──────────────────────┤
│    CITIZENS      │   AUTHORITIES     │      ADMINS          │
│ File complaints  │ Review & track    │ Manage system        │
│ Chat with bot    │ Filter by thana   │ View analytics       │
│ Download docs    │ Add updates       │ Search all           │
└────────┬─────────┴────────┬──────────┴──────────┬─────────────┘
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            │
     ┌──────────────────────▼───────────────────────────┐
     │   DJANGO WEB APPLICATION                        │
     ├────────────────────────────────────────────────┤
     │ • URL Routing (15+ endpoints)                  │
     │ • Authentication & Authorization               │
     │ • Business Logic (views.py, views_chatbot.py) │
     │ • ORM Data Models (6 models)                   │
     │ • Form Validation & Processing                │
     └──────────────────────────────────────────────┘
                            │
     ┌──────────────────────▼───────────────────────────┐
     │   SERVICE LAYER                                 │
     ├────────────────────────────────────────────────┤
     │ ┌──────────────────────────────────────────┐   │
     │ │ Groq LLM Service                         │   │
     │ │ • chat() - Conversational responses      │   │
     │ │ • extract_complaint_info() - Parsing     │   │
     │ │ • Model: Mixtral-8x7b-32768             │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ Image Analysis Service                   │   │
     │ │ • analyze_complaint_image()              │   │
     │ │ • Model: Llama-4-Scout-17B-16e         │   │
     │ │ • Extracts issue details from photos   │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ RAG (Retrieval-Augmented Generation)    │   │
     │ │ • retrieve() - Get policy context       │   │
     │ │ • _embed_text() - 384D vectors          │   │
     │ │ • ChromaDB backend (local)              │   │
     │ │ • SentenceTransformers embedder         │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ Web Search Service (Tavily)             │   │
     │ │ • search_for_verification()             │   │
     │ │ • validate_against_policy()             │   │
     │ │ • Fact-checking & validation            │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ Document Service                         │   │
     │ │ • generate() - PDF & DOCX files         │   │
     │ │ • ReportLab & python-docx               │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ Email Service                            │   │
     │ │ • send_complaint_to_authority()         │   │
     │ │ • send_citizen_confirmation()           │   │
     │ └──────────────────────────────────────────┘   │
     │                                                │
     │ ┌──────────────────────────────────────────┐   │
     │ │ Additional Services                      │   │
     │ │ • ComplaintSubmissionService             │   │
     │ │ • DocumentStorageService                 │   │
     │ │ • Area Routing Logic                     │   │
     │ └──────────────────────────────────────────┘   │
     └────────────────────────────────────────────────┘
                            │
     ┌──────────────────────▼───────────────────────────┐
     │   EXTERNAL SERVICES                             │
     ├────────────────────────────────────────────────┤
     │ • Groq API (Chat & Vision)                     │
     │ • Tavily API (Web Search)                      │
     │ • SMTP Server (Email)                          │
     │ • Supabase (Optional: pgvector, Storage)       │
     └────────────────────────────────────────────────┘
                            │
     ┌──────────────────────▼───────────────────────────┐
     │   DATA PERSISTENCE                              │
     ├────────────────────────────────────────────────┤
     │ • SQLite (db.sqlite3) - Primary Database       │
     │ • ChromaDB - Local Vector Store                │
     │ • File Storage (local or Supabase)             │
     │ • Policy Documents Cache                       │
     └────────────────────────────────────────────────┘
```

### Data Flow: Complaint Filing Process

```
1. USER CHAT
   Input: "There's a pothole on Road X for 2 months"
   
2. GROQ LLM (Mixtral-8x7b-32768)
   ├─ Process conversation history
   ├─ Generate conversational response
   ├─ After 2+ messages, extract structured data
   └─ Output: category, area, duration, keywords

3. POLICY RETRIEVAL (RAG + ChromaDB)
   ├─ Embed user message (SentenceTransformers)
   ├─ Search vector database for similar policies
   └─ Retrieve Bangla/English policy context

4. WEB SEARCH (Tavily)
   ├─ Search for real-world verification
   ├─ Find current reports on issue type
   └─ Validate complaint feasibility

5. INCONSISTENCY SCORING
   ├─ Compare extracted info with policy
   ├─ Compare with web search results
   └─ Generate score (1=consistent, 5=highly inconsistent)

6. IMAGE ANALYSIS (Optional)
   ├─ If image uploaded, use Groq Vision (Llama-4-Scout)
   ├─ Extract infrastructure details from photo
   └─ Enhance complaint description

7. COMPLAINT STORAGE
   ├─ Save to database
   ├─ Generate PDF & DOCX
   ├─ Assign to appropriate authority

8. NOTIFICATIONS
   ├─ Email authority notification with documents
   ├─ Send citizen confirmation copy
   └─ Track email delivery
```

---

## Core Features

### 1. Citizen Portal

#### Features
- **Modern Chat Interface** - Talk to Dhaka Nagorik AI in Bangla or English
- **Intelligent Complaint Extraction** - AI automatically identifies complaint details
- **File Complaints** - Submit formal complaint applications with just a chat
- **Upload Evidence** - Attach images, documents to support complaints
- **Track Status** - Real-time updates on complaint progress
- **Download Documents** - Get PDF/DOCX versions of complaints
- **Conversation History** - Access past chat sessions and complaints

#### Key Benefits
- No complex forms to fill out
- Multi-language support (Bangla & English)
- Conversational and user-friendly
- Automatic area-based authority routing

---

### 2. Authority Dashboard

#### Features
- **Thana-Specific View** - See only complaints for their service area
- **Filter & Search** - Find complaints by status, category, date
- **Complaint Details** - View full information with citizen contact
- **Add Updates** - Respond to citizens with status changes
- **Track Progress** - Monitor which complaints are resolved
- **Download Evidence** - Access attached images and documents
- **Email Notifications** - Auto-receive new complaints assigned

#### Key Benefits
- Streamlined workflow
- Location-based organization
- Audit trail of all changes
- Direct communication with citizens

---

### 3. Admin Dashboard

#### Features
- **System-Wide Overview** - See all complaints across Dhaka
- **Advanced Search** - Filter by date, status, category, authority, citizen
- **User Management** - Approve/reject authority registrations
- **Analytics** - Statistics on complaint types, resolution times
- **Authority Assignment** - Manually reassign complaints if needed
- **System Configuration** - Manage email, storage, AI settings
- **Export Reports** - Generate complaint data reports

#### Key Benefits
- Full system visibility
- Troubleshooting capabilities
- Data-driven insights
- Administrative control

---

### 4. AI-Powered Chatbot

#### Capabilities
- **Multi-Turn Conversations** - Natural back-and-forth dialogue
- **Complaint Extraction** - Automatically identifies:
  - Category (pothole, water, garbage, electricity, noise, health, environment, other)
  - Location (Dhaka thana/area)
  - Duration (how long issue exists)
  - Keywords and details
  
- **Policy Context Injection** - Provides relevant municipal policy information
- **Web Search Integration** - Fact-checks complaints against real-world data
- **Inconsistency Scoring** - Rates likelihood of complaint validity (1-5 scale)
- **Language Support** - Works seamlessly in Bangla and English
- **Empathetic Responses** - Designed to be friendly and helpful

#### Technical Details
- **Model**: Mixtral-8x7b-32768 (Groq)
- **Temperature**: 0.4 (lower = more consistent)
- **Max Tokens**: 1024
- **Context**: Includes system prompt + policy context + validation info

---

### 5. Vision Analysis for Evidence

#### Capabilities
- **Image Upload** - Citizens can attach photos of complaints
- **Automatic Analysis** - AI analyzes images to:
  - Identify infrastructure issue type
  - Assess severity
  - Extract location clues
  - Describe visible damage/problems
  
- **Enhanced Descriptions** - Vision analysis automatically improves complaint description
- **Evidence Storage** - Images stored securely with complaint

#### Technical Details
- **Model**: meta-llama/llama-4-scout-17b-16e-instruct (Groq Vision)
- **Supported Formats**: JPEG, PNG, WebP, GIF
- **Max Size**: 8 MB per image
- **Max Images**: 5 per message
- **Processing**: Base64 encoding + API call

---

### 6. Policy & Knowledge Base (RAG)

#### Capabilities
- **Policy Document Indexing** - Automatically indexes municipal policy PDFs
- **Vector Search** - Retrieves relevant policies using semantic search
- **384-Dimensional Embeddings** - High-quality multilingual text representations
- **Similar Complaint Detection** - Finds comparable past complaints
- **Context Injection** - Adds policy context to LLM for better responses
- **Offline Fallback** - Hash-based embeddings if transformer model unavailable

#### Technical Details
- **Vector Store**: ChromaDB (local) or Supabase pgvector (hosted)
- **Embedding Model**: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **Embedding Dimension**: 384 (default)
- **Chunk Size**: 1200 characters with 200-char overlap
- **Collections**: 
  - `policy_documents` - Municipal policies
  - `complaints` - Similar complaint summaries
- **Search Type**: Cosine similarity

---

### 7. Document Generation

#### PDF Generation
- **Technology**: ReportLab
- **Content**:
  - Formal application letter
  - Complaint reference number (DN-XXXXX)
  - Recipient details (authority info)
  - Structured complaint description
  - Category and area
  - Timestamp
  - Citizen signature block
  - Professional formatting

#### DOCX Generation
- **Technology**: python-docx
- **Content**: Same as PDF
- **Advantages**: Editable by authorities for annotations

#### Storage Options
- **Local**: `storage/complaint_documents/{complaint_id}/`
- **Supabase Storage**: `complaint-documents` bucket with signed URLs

#### Delivery
- Attached to authority email
- Available for download in citizen dashboard
- Audit trail of generation timestamps

---

### 8. Email Notifications

#### Authority Notification
- **Trigger**: When complaint assigned to authority
- **Content**:
  - Complaint ID
  - Category
  - Service area
  - Description
  - Citizen contact info
  - Generated PDF/DOCX attached
  
#### Citizen Confirmation
- **Trigger**: After complaint filed
- **Content**:
  - Reference number
  - Confirmation of receipt
  - Expected response timeline
  - Copy of complaint details

#### Technical Details
- **Protocol**: SMTP
- **Sender**: Configurable from environment
- **Attachments**: PDF & DOCX documents
- **Error Handling**: Logged but doesn't block complaint filing

---

### 9. Area Routing & Authority Assignment

#### Features
- **Automatic Routing** - Complaints assigned based on:
  - City Corporation (DNCC, DSCC)
  - Ward Number (1-75)
  - Thana name
  
- **Authority Matching** - Finds approved authority covering service area
- **Manual Override** - Admin can reassign if needed
- **Location Normalization** - Handles various spelling/naming variations
- **Service Area Validation** - Checks if location exists in Dhaka

#### Database Unique Constraints
- Only one approved authority per city corporation + ward number combination
- Prevents duplicate routing

---

### 10. Multi-Role Authentication

#### User Types
1. **Citizen** - Can file complaints and chat
2. **Authority** - Can view and manage complaints for their area
3. **Admin** - Full system access

#### Features
- **Secure Login** - Django authentication with session management
- **Registration** - Citizens can self-register
- **Authority Approval** - Admin must approve authority accounts
- **Password Management** - Secure password hashing
- **Permission Control** - View/edit restrictions based on role

---

## AI/ML Models & Services

### 1. Groq LLM Service (Mixtral-8x7b-32768)

#### Purpose
- Chat interface for complaint collection
- Information extraction from conversations
- Policy context integration
- Conversational response generation

#### Configuration
```python
MODEL = "mixtral-8x7b-32768"
TEMPERATURE = 0.4
MAX_TOKENS = 1024
```

#### Key Methods
```python
chat(conversation_history, system_prompt, policy_context, validation_context)
    # Returns: Assistant response string
    
extract_complaint_info(conversation_text, policy_context)
    # Returns: Structured complaint dict with category, area, duration, score
```

#### Features
- Multi-turn conversation support
- Policy context injection
- Validation context injection
- Message normalization (removes incomplete/invalid messages)
- Supports both Bangla and English

---

### 2. Vision Analysis Service (Llama-4-Scout)

#### Purpose
- Analyze complaint images
- Extract infrastructure issue details
- Assess severity and impact
- Enhance complaint descriptions

#### Configuration
```python
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
```

#### Key Methods
```python
analyze_complaint_image(image_path)
    # Returns: Analysis dict with issue type, severity, location clues, etc.
    
analyze_complaint_image_bytes(image_bytes, filename, mime_type)
    # Returns: Analysis dict from raw bytes
```

#### Capabilities
- Identifies infrastructure issues (pothole, water leak, garbage, etc.)
- Assesses damage severity
- Detects location landmarks
- Generates structured analysis
- Handles multiple image formats

---

### 3. RAG Service (Vector Search + Embeddings)

#### Purpose
- Retrieve relevant policy documents
- Find similar past complaints
- Inject context into LLM
- Enable knowledge-based assistance

#### Configuration
```python
EMBEDDING_DIMENSION = 384
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 1200
OVERLAP = 200
```

#### Key Methods
```python
retrieve(query, n_results=3)
    # Returns: Similar policies and complaints
    
_embed_text(text)
    # Returns: 384-dimensional vector
    
_chunk_text(text, chunk_size=1200, overlap=200)
    # Returns: List of overlapping text chunks
```

#### Features
- Automatic text chunking with overlap
- Multilingual embeddings
- Local ChromaDB or Supabase pgvector
- Cosine similarity search
- Metadata tracking (category, source, etc.)
- Fallback hash-based embeddings if model unavailable

---

### 4. Web Search Service (Tavily)

#### Purpose
- Fact-check complaint claims
- Validate against real-world data
- Verify policy applicability
- Assess inconsistency score

#### Configuration
```python
PROVIDER = "Tavily"
MAX_RESULTS = 5
INCLUDE_ANSWER = True
```

#### Key Methods
```python
search_for_verification(query, max_results=5)
    # Returns: List of search results with sources
    
validate_against_policy(complaint, policies=[])
    # Returns: Validation result with inconsistencies and policy refs
```

#### Features
- Real-time web search
- AI-powered answer extraction
- Source attribution
- Relevance scoring
- Policy comparison
- Inconsistency detection
- Thana validation against known list

---

### 5. Document Generation Service

#### PDF Generation
```python
generate(complaint, extracted_complaint, attachments)
    # Returns: PDF bytes
```

#### DOCX Generation
```python
_generate_docx(complaint, extracted_complaint, attachments)
    # Returns: DOCX bytes
```

#### Content Includes
- Formal application format
- Complaint reference number
- Date and recipient
- Subject line
- Description with policy references
- Citizen signature block

#### Storage
- Local filesystem: `storage/complaint_documents/`
- Supabase Storage: Configurable bucket
- Signed URLs for download (if Supabase)

---

### 6. Email Delivery Service

#### Methods
```python
send_complaint_to_authority(complaint, attachment_paths)
    # Sends to assigned authority
    
send_citizen_confirmation(complaint, attachment_paths)
    # Sends to citizen
```

#### Features
- SMTP configuration
- Attachment support (PDF/DOCX)
- Error handling and logging
- Configurable sender info
- HTML/Text body support
- Rate limiting (via Django)

---

### 7. Vector Store Backends

#### Local Backend: ChromaDB
- In-process vector database
- Persistent storage in `./chroma_data/`
- No external dependencies required
- Fast for development

#### Hosted Backend: Supabase pgvector
- PostgreSQL with pgvector extension
- Centralized storage
- Scalable for production
- Supports multiple deployments

#### Configuration
```env
VECTOR_STORE_BACKEND=chroma  # or 'supabase'
VECTOR_PERSIST_DIR=./chroma_data
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
SUPABASE_VECTOR_TABLE=vector_documents
```

---

## Database Schema

### Models Overview

```
UserProfile (1:1 with User)
├─ user (FK to User)
├─ role (citizen/authority/admin)
├─ thana (optional, for authorities)
├─ city_corporation (DNCC/DSCC)
├─ ward_number (1-75)
├─ department (for authorities)
├─ employee_id
├─ phone_number
├─ approval_status
├─ created_at
└─ updated_at

Complaint (FK to User)
├─ citizen (FK to User)
├─ category (environment/health/water/electricity/roads/other)
├─ city_corporation
├─ ward_number
├─ thana
├─ area
├─ description
├─ status (submitted/acknowledged/under_review/in_progress/awaiting_confirmation/resolved/closed)
├─ assigned_authority (FK to User)
├─ created_at
├─ updated_at
├─ acknowledged_at
├─ resolved_at
├─ email_sent_at
├─ email_error
├─ generated_docx_path
├─ generated_pdf_path
└─ last_reminder_sent_at

ChatSession (FK to User)
├─ user (FK to User)
├─ title (auto-generated from first message)
├─ language (detected or selected)
├─ generated_complaint (FK to Complaint, optional)
├─ created_at
├─ updated_at
└─ is_active

ChatMessage (FK to ChatSession)
├─ chat_session (FK to ChatSession)
├─ role (user/assistant)
├─ content (text message)
├─ created_at
└─ metadata (JSON)

ChatAttachment (FK to ChatMessage)
├─ message (FK to ChatMessage)
├─ file (FileField: image)
├─ uploaded_at
└─ file_type

ExtractedComplaint (FK to ChatSession)
├─ chat_session (FK to ChatSession)
├─ category
├─ area
├─ duration
├─ keywords (JSON array)
├─ inconsistency_score (1-5)
├─ extracted_at
└─ metadata (JSON)

ComplaintUpdate (FK to Complaint)
├─ complaint (FK to Complaint)
├─ updated_by (FK to User)
├─ new_status
├─ response_text
├─ created_at
└─ attachment (FileField)
```

### Key Relationships

- **User ↔ UserProfile**: One-to-one (extended user profile)
- **User ↔ Complaint**: One-to-many (citizen files multiple complaints)
- **User ↔ ChatSession**: One-to-many (citizen has multiple chat sessions)
- **ChatSession ↔ ChatMessage**: One-to-many (session contains messages)
- **ChatSession ↔ ExtractedComplaint**: One-to-one (extracted info from chat)
- **ChatSession ↔ Complaint**: One-to-one (chat can generate complaint)
- **ChatMessage ↔ ChatAttachment**: One-to-many (message can have images)
- **Complaint ↔ ComplaintUpdate**: One-to-many (complaint has history)
- **Complaint ↔ Authority**: Many-to-one (multiple assigned to one authority)

---

## API Endpoints

### Authentication (4 endpoints)

```
POST /signup/
├─ Body: email, password, full_name, phone_number
├─ Response: Redirect to login on success
└─ Role: Public

POST /login/
├─ Body: email, password
├─ Response: Redirect to role-specific dashboard
└─ Role: Public

POST /logout/
├─ Response: Redirect to home
└─ Role: Authenticated

GET /
├─ Response: Redirect to appropriate dashboard
└─ Role: Authenticated
```

### Dashboards (3 endpoints)

```
GET /citizen/
├─ Response: Complaint filing interface + chat
├─ Features: File complaint, view history
└─ Role: Citizen

GET /authority/
├─ Response: Thana-specific complaint view
├─ Features: Filter by status, add updates
└─ Role: Authority

GET /admin/
├─ Response: System-wide dashboard
├─ Features: Full search, user management, analytics
└─ Role: Admin
```

### Complaint Management (3 endpoints)

```
GET /complaint/<id>/
├─ Response: Complaint details + full history
├─ Features: View updates, download documents
└─ Role: Citizen (own) / Authority (assigned) / Admin

POST /complaint/<id>/
├─ Body: status, response_text, attachment
├─ Response: Updated complaint
└─ Role: Authority (assigned) / Admin

GET /complaint/<id>/document/<format>/
├─ Params: format (pdf or docx)
├─ Response: File download
└─ Role: Citizen (own) / Authority (assigned) / Admin
```

### Chatbot (5 endpoints)

```
GET /chatbot/
├─ Response: Chat interface
└─ Role: Authenticated

POST /chatbot/session/create/
├─ Body: initial_message (optional), attachments
├─ Response: {session_id, title, message_id}
└─ Role: Authenticated

GET /chatbot/session/<id>/
├─ Response: Full chat history with messages
├─ Includes: Messages, attachments, extracted complaint
└─ Role: Authenticated

POST /chatbot/session/<id>/message/
├─ Body: message_text, attachments
├─ Response: {assistant_message, extracted_complaint, keywords}
└─ Role: Authenticated

POST /chatbot/session/<id>/close/
├─ Body: file_complaint (boolean)
├─ Response: Complaint ID if filed, or confirmation
└─ Role: Authenticated
```

### Response Format

All endpoints return JSON:
```json
{
  "success": true/false,
  "data": {...},
  "error": "error message if any",
  "timestamp": "ISO-8601"
}
```

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- Virtual environment (`.venv/`)
- API Keys: Groq, Tavily
- Optional: PostgreSQL, Supabase

### Installation Steps

#### 1. Clone & Setup Environment
```bash
cd "d:\Codes\Dhaka Nagorik Bot"
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
source .venv/bin/activate      # Mac/Linux
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables
```bash
# Create .env file with:
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=mixtral-8x7b-32768
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

TAVILY_API_KEY=your-tavily-api-key

# Email (optional)
ENABLE_EMAIL=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
EMAIL_FROM_NAME=Dhaka Nagorik AI

# Vector Store (local default)
VECTOR_STORE_BACKEND=chroma
VECTOR_PERSIST_DIR=./chroma_data

# Optional: Supabase Storage
# ENABLE_SUPABASE_STORAGE=true
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=your-key
# SUPABASE_MEDIA_BUCKET=complaint-media
# SUPABASE_DOCUMENT_BUCKET=generated-documents
```

#### 4. Apply Migrations
```bash
python manage.py migrate
```

#### 5. Create Test Users (Optional)
```bash
python setup_users.py
```

#### 6. Run Development Server
```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

### Test Accounts

| Email | Password | Role |
|-------|----------|------|
| citizen@example.com | Citizen@1234 | Citizen |
| authority@dhaka.gov | Authority@1234 | Authority |
| admin@dhaka.gov | Admin@1234 | Admin |

---

## Deployment Options

### Local Development
- SQLite database
- Local ChromaDB
- Local file storage
- Flet desktop app (optional)

### Production Deployment

#### Option 1: Django on Heroku/PythonAnywhere
```bash
pip freeze > requirements.txt
git push heroku main
heroku run python manage.py migrate
```

#### Option 2: Docker Deployment
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "dhaka_web.wsgi:application", "--bind", "0.0.0.0:8000"]
```

#### Option 3: Managed Platform (PythonAnywhere, AWS, DigitalOcean)
- Use PostgreSQL instead of SQLite
- Enable Supabase Storage for file uploads
- Enable Supabase pgvector for scalable RAG
- Use dedicated SMTP service (SendGrid, AWS SES)
- Configure CDN for static files

### Database Migration to PostgreSQL

```bash
pip install psycopg[binary]>=3.1,<4

# Update .env
DATABASE_URL=postgresql://user:password@host:5432/dbname

python manage.py migrate
```

### Supabase Integration

```bash
pip install supabase==2.4.5

# Run schema setup (one-time)
# Copy contents of supabase/schema.sql into Supabase SQL editor

# Update .env
VECTOR_STORE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
ENABLE_SUPABASE_STORAGE=true
```

---

## File Structure

```
Dhaka Nagorik Bot/
├── manage.py                          # Django CLI
├── db.sqlite3                         # SQLite database
├── requirements.txt                   # Python dependencies
├── .env                               # Environment variables
├── .env.example                       # Example env template
│
├── dhaka_web/                         # Django project config
│   ├── __init__.py
│   ├── settings.py                    # All configuration
│   ├── urls.py                        # Project-level routing
│   ├── wsgi.py                        # Production WSGI
│   └── asgi.py                        # ASGI for async
│
├── complaints/                        # Main Django app
│   ├── __init__.py
│   ├── models.py                      # 6 database models
│   ├── views.py                       # Main views (auth, dashboards)
│   ├── views_chatbot.py               # Chat API endpoints
│   ├── forms.py                       # Django forms
│   ├── urls.py                        # App-level routing
│   ├── admin.py                       # Django admin config
│   ├── apps.py                        # App configuration
│   ├── tests.py                       # Unit tests (minimal)
│   ├── area_routing.py                # Location routing logic
│   │
│   ├── services/                      # Business logic layer
│   │   ├── __init__.py
│   │   ├── groq_service.py            # LLM (Mixtral-8x7b)
│   │   ├── rag_service.py             # Vector search
│   │   ├── image_analysis_service.py  # Vision (Llama-4-Scout)
│   │   ├── web_search_service.py      # Tavily search
│   │   ├── email_service.py           # SMTP delivery
│   │   ├── document_service.py        # PDF/DOCX generation
│   │   ├── document_storage_service.py# File storage abstraction
│   │   ├── vector_store.py            # ChromaDB/Supabase abstraction
│   │   ├── complaint_submission_service.py # Workflow orchestration
│   │   └── __pycache__/
│   │
│   ├── migrations/                    # Database migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_chatsession_chatmessage_extractedcomplaint.py
│   │   ├── 0003_chatsession_generated_complaint.py
│   │   ├── 0004_complaint_email_fields.py
│   │   ├── 0005_complaint_acknowledged_at.py
│   │   ├── 0006_complaintattachment.py
│   │   └── 0007_*.py (future migrations)
│   │
│   ├── management/                    # Custom management commands
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── index_policies.py      # Index policy PDFs
│   │       └── sync_supabase_storage.py
│   │
│   └── templates/                     # Rendered by server
│       └── complaints/
│           ├── base.html              # Base template
│           ├── login.html
│           ├── signup.html
│           ├── citizen_dashboard.html # File complaint UI
│           ├── authority_dashboard.html
│           ├── admin_dashboard.html
│           ├── complaint_detail.html
│           └── chatbot.html           # Chat interface
│
├── templates/                         # Root templates
│   └── complaints/                    # (symlink or structure)
│
├── static/                            # CSS, JS, images
│   ├── css/
│   │   ├── tailwind.css
│   │   └── custom.css
│   ├── js/
│   │   ├── chat.js
│   │   └── dashboard.js
│   └── images/
│
├── storage/                           # File storage (local)
│   ├── complaint_documents/
│   │   └── {complaint_id}/
│   │       └── complaint_{id}_{timestamp}.pdf/docx
│   ├── chat_attachments/
│   │   └── {session_id}/
│   │       └── {image_files}
│   ├── generated_docs/
│   └── policies/
│       └── *.pdf (policy documents)
│
├── chroma_data/                       # Vector database (local)
│   └── (ChromaDB persistent storage)
│
├── _archive/                          # Historical docs
│   ├── GAP_ANALYSIS.md
│   ├── IMPLEMENTATION_REVIEW.md
│   ├── PHASE_1_COMPLETE.md
│   ├── PHASE_2_COMPLETE.md
│   ├── UPGRADE_PLAN.md
│   ├── docs/
│   │   ├── ai_pipeline.md
│   │   ├── architecture.md
│   │   ├── setup_guide.md
│   │   └── workflow.md
│   ├── scripts/
│   └── storage/
│       ├── authorities.json
│       └── complaints.json
│
├── supabase/                          # Supabase config
│   ├── schema.sql                     # pgvector setup
│   └── migrations/
│       ├── 001_phase1_city_corporation_and_email.sql
│       └── 002_phase2_conversations.sql
│
├── modern_chat_ui.py                  # Desktop app (Flet)
├── create_user.py                     # User creation script
├── setup_users.py                     # Initial setup script
├── check_users.py                     # User verification script
│
├── README.md                          # Basic overview
├── QUICK_REFERENCE.md                 # Quick lookup
├── CHATBOT_README.md                  # RAG setup guide
├── CODEBASE_ANALYSIS.md               # Detailed analysis
├── VISUAL_SYSTEM_MAP.md               # Architecture diagrams
└── PROJECT_REVIEW.md                  # THIS FILE
```

---

## Configuration Reference

### Environment Variables

#### Required Variables

```env
# Groq LLM
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=mixtral-8x7b-32768
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

# Tavily Web Search
TAVILY_API_KEY=your-tavily-api-key

# Django
SECRET_KEY=your-django-secret-key
DEBUG=True  # Set False in production
ALLOWED_HOSTS=localhost,127.0.0.1
```

#### Optional: Email Configuration

```env
ENABLE_EMAIL=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-specific-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
EMAIL_FROM_NAME=Dhaka Nagorik AI System
```

#### Optional: Database Configuration

```env
# PostgreSQL (if not SQLite)
DATABASE_URL=postgresql://user:password@localhost:5432/dhaka_db

# Or individual settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dhaka_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_SSLMODE=require
```

#### Optional: Vector Store Configuration

```env
# Local ChromaDB (default)
VECTOR_STORE_BACKEND=chroma
VECTOR_PERSIST_DIR=./chroma_data
ENABLE_AUTO_POLICY_INDEXING=false

# OR Supabase pgvector
VECTOR_STORE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_VECTOR_TABLE=vector_documents
SUPABASE_VECTOR_MATCH_FUNCTION=match_vector_documents
```

#### Optional: Storage Configuration

```env
# Local file storage (default)
USE_SUPABASE_STORAGE=False

# OR Supabase Storage
USE_SUPABASE_STORAGE=True
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_MEDIA_BUCKET=complaint-media
SUPABASE_DOCUMENT_BUCKET=generated-documents
SUPABASE_STORAGE_SIGNED_URL_TTL=3600  # 1 hour
```

---

## Summary

**Dhaka Nagorik Bot** is a production-ready, AI-powered civic complaint management system featuring:

### Technology Highlights
- ✅ **Groq Mixtral-8x7b** for intelligent chat and extraction
- ✅ **Groq Llama-4-Scout** for image analysis
- ✅ **Tavily** for fact-checking and web search
- ✅ **ChromaDB/Supabase** for RAG and vector search
- ✅ **SentenceTransformers** for 384-dimensional embeddings
- ✅ **Django 6.0.4** as the web framework
- ✅ **ReportLab & python-docx** for document generation
- ✅ **Multiple storage backends** (local & Supabase)

### Feature Completeness
- ✅ Core complaint filing workflow
- ✅ Multi-role authentication and dashboards
- ✅ AI-powered chatbot with RAG
- ✅ Image analysis for evidence
- ✅ Automatic document generation
- ✅ Email notifications
- ✅ Area-based authority routing
- ✅ Real-time status tracking

### Phase Status
- **Phase 1**: ✅ Complete (Basic system, authentication, dashboards)
- **Phase 2**: ✅ Complete (AI integration, RAG, document generation, email)
- **Phase 3**: 📋 Planned (Analytics, advanced reporting, mobile app)

### Deployment Ready
- ✅ Local development mode
- ✅ Production-ready with PostgreSQL
- ✅ Cloud deployment support (Heroku, AWS, DigitalOcean)
- ✅ Supabase integration available
- ✅ Docker containerization ready

---

**Last Updated:** April 17, 2026  
**Version:** Phase 2 Complete  
**Maintained By:** Dhaka Nagorik Development Team
