# 📋 Dhaka Nagorik Bot - Quick Reference Card

## 🏃 Quick Start
```bash
cd "d:\Codes\Dhaka Nagorik Bot"
.\.venv\Scripts\Activate.ps1
python manage.py runserver
# Visit: http://127.0.0.1:8000/
```

## 📊 System Status
- **Phase**: 2 (Complete) → Phase 3 (Planned)
- **Core Features**: ✅ 95% Complete
- **Services**: ✅ All integrated
- **Testing**: ⚠️ Minimal coverage
- **Deployment**: 🔴 Not ready (development only)

## 🗂️ File Locations

### Core Django
- `complaints/models.py` - 6 models (User, Complaint, Chat, Update, Attachment, Extracted)
- `complaints/views.py` - Auth, dashboards (citizen/authority/admin)
- `complaints/views_chatbot.py` - Chat endpoints (4 routes)
- `dhaka_web/settings.py` - Configuration

### Services (`complaints/services/`)
- `groq_service.py` - LLM (Mixtral-8x7b)
- `rag_service.py` - Vector search (ChromaDB)
- `email_service.py` - SMTP notifications
- `web_search_service.py` - Tavily fact-checking
- `document_service.py` - PDF/DOCX generation

### Frontend
- `templates/complaints/chatbot.html` - Main chat UI
- `templates/complaints/citizen_dashboard.html` - Filing UI
- `templates/complaints/authority_dashboard.html` - Authority view
- `modern_chat_ui.py` - Flet desktop (partial)

## 🔌 API Endpoints (15 total)

### Auth (4)
- `POST /signup/` - Register
- `POST /login/` - Login
- `POST /logout/` - Logout
- `GET /` - Redirect to dashboard

### Dashboards (3)
- `GET /citizen/` - File complaints
- `GET /authority/` - Thana-filtered view
- `GET /admin/` - Full system view

### Complaints (3)
- `GET /complaint/<id>/` - Details + history
- `POST /complaint/<id>/` - Add update
- `GET /complaint/<id>/document/<fmt>/` - Download PDF/DOCX

### Chatbot (5)
- `GET /chatbot/` - Chat page
- `POST /chatbot/session/create/` - New chat
- `GET /chatbot/session/<id>/` - Get history
- `POST /chatbot/session/<id>/message/` - Send message
- `POST /chatbot/session/<id>/close/` - End + file complaint

## 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 6.0.4 | Web framework |
| groq | 0.10.0 | LLM API |
| chromadb | 0.5.0 | Vector DB |
| sentence-transformers | 3.0.0 | Embeddings |
| tavily-python | 0.3.4 | Web search |
| python-docx | 1.1.2 | DOCX generation |
| reportlab | 4.2.5 | PDF generation |

## 🔑 Required Environment Variables

```env
# LLM
GROQ_API_KEY=your-groq-key

# Search
TAVILY_API_KEY=your-tavily-key

# Email (if enabled)
ENABLE_EMAIL=True
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Django
SECRET_KEY=django-insecure-key
DEBUG=True
```

## 💾 Models (6 total)

```
UserProfile → User (1:1)
  ├─ role: citizen/authority/admin
  └─ thana: location

Complaint → User (1:N)
  ├─ category: 6 options
  ├─ status: 5 stages
  ├─ assigned_authority: User
  ├─ ExtractedComplaint (1:1 optional)
  ├─ ComplaintUpdate (1:N history)
  └─ generated_docx_path, generated_pdf_path

ChatSession → User (1:N)
  ├─ generated_complaint: Reference
  ├─ language: en/bn
  └─ ChatMessage (1:N)
      └─ ChatAttachment (1:N images)
```

## ✅ Working Features

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-role auth | ✅ | Citizen, Authority, Admin |
| Complaint filing | ✅ | Web form + AI chat hybrid |
| Status tracking | ✅ | 5-stage lifecycle |
| Groq LLM | ✅ | Bangla + English support |
| RAG system | ✅ | ChromaDB + embeddings |
| Email notifications | ✅ | With document attachments |
| PDF/DOCX generation | ✅ | Auto on filing |
| Chat sessions | ✅ | Multi-turn with history |
| Authority dashboard | ✅ | Thana-filtered view |
| Admin dashboard | ✅ | Full system view + search |

## 🔧 Partial Features

| Feature | % Done | Gap |
|---------|--------|-----|
| Desktop UI | 30% | Needs auth header integration |
| Image analysis | 60% | Stored but not analyzed by AI |
| Real-time notifications | 40% | Email-only, no WebSocket |
| Analytics dashboard | 30% | Basic counts only |
| Policy RAG | 50% | System ready, PDFs needed |

## ❌ Known Issues

1. **Policy PDFs not loaded** - Folder ready (`storage/policies/`), need to add PDFs
2. **Desktop UI broken** - Auth headers missing (documented in auth-headers-fix.md)
3. **No test coverage** - tests.py minimal
4. **Single SQLite DB** - Not production-ready
5. **No rate limiting** - Groq/Tavily APIs unprotected

## 🚀 Phase 3 Roadmap

1. Load policy PDF documents
2. Add comprehensive unit tests
3. Fix & integrate Flet desktop UI
4. Implement WebSocket notifications
5. Add complaint ratings system
6. Setup production database (PostgreSQL)

## 📈 Performance

| Metric | Current | Target |
|--------|---------|--------|
| Page load | ~500ms | <200ms |
| Chat response | 2-3s | <1s (Groq limited) |
| Document gen | 1-2s | <500ms |
| Search | ~1s | <500ms |

## 🔒 Security Status

- ✅ CSRF protection enabled
- ✅ SQL injection safe (Django ORM)
- ✅ Authentication required on endpoints
- ✅ File upload validation
- ⚠️ DEBUG mode ON (disable for production)
- ⚠️ Secret key exposed (move to .env)
- ⚠️ ALLOWED_HOSTS empty (set for deployment)

## 💡 Pro Tips

1. **Modify chat prompt**: Edit `groq_service.py` system_prompt
2. **Add policy docs**: Drop PDFs in `storage/policies/` → RAGService loads them
3. **Change complaint categories**: Edit `Complaint.CATEGORY_CHOICES` in models
4. **Test email**: `python setup_users.py` then file complaint
5. **Clear ChromaDB cache**: Delete `.chroma/` folder, restart

## 📝 Important Notes

- **Extraction trigger**: Needs 2+ messages in chat
- **Authority filtering**: Automatic by thana from profile
- **Email fallback**: Set `ENABLE_EMAIL=False` to skip SMTP
- **RAG fallback**: Hash-based embeddings if SentenceTransformers fails
- **Groq throttling**: Monitor API usage (free tier has limits)

## 🎯 Next Priorities

1. **Urgent**: Load policy PDFs (RAG system ready, just needs files)
2. **High**: Fix Flet UI auth headers + integration
3. **High**: Add pytest test suite
4. **Medium**: Implement real-time WebSocket notifications
5. **Medium**: Setup PostgreSQL for production

---

**Last Updated**: April 15, 2026
**Status**: Phase 2 Complete ✅
**Files**: 32 Python + 8 HTML templates
