# RAG Chatbot System - Setup Guide

## 🤖 What This Does

The **RAG Chatbot** is the core feature of your complaint system. It:

1. **Listens to user complaints** in Bangla or English
2. **Extracts structured data**:
   - Category (pothole, water, garbage, etc.)
   - Area/Thana in Dhaka
   - Duration of the issue
3. **Compares with policy** using ChromaDB (Bangla policy docs)
4. **Validates with web search** via Tavily to check reality vs. policy
5. **Scores inconsistency** (1-5 scale, 1=consistent, 5=highly inconsistent)
6. **Shows extracted keywords** to the user in real-time

## 🔑 Required API Keys

### 1. Groq API Key (LLM)
- Get from: https://console.groq.com/
- Model used: `mixtral-8x7b-32768` (fast and free tier available)
- Add to `.env`:
  ```
  GROQ_API_KEY=your-api-key-here
  ```

### 2. Tavily API Key (Web Search)
- Get from: https://tavily.com/
- Used for fact-checking and validating complaints
- Add to `.env`:
  ```
  TAVILY_API_KEY=your-api-key-here
  ```

### 3. ChromaDB (Already Included)
- Vector database for RAG
- Runs locally, no API key needed
- Stores Bangla policy documents

## 📦 Architecture

```
User Login
    ↓
Chat Page (Modern UI with sidebar)
    ↓
Input: "Pothole on Road X for 2 months"
    ↓
Groq LLM (Mixtral-8x7b-32768)
    ├─ Extract: category, area, duration
    ├─ Generate conversational response
    └─ Return structured data
    ↓
ChromaDB RAG
    ├─ Search policy for "pothole"
    ├─ Find matching policy document (Bangla)
    └─ Return relevant policy
    ↓
Tavily Web Search
    ├─ Search: "pothole Dhaka infrastructure"
    ├─ Validate against real-world reports
    └─ Return relevance score
    ↓
Inconsistency Checker
    ├─ Compare extracted info with policy
    ├─ Compare with web search results
    └─ Score 1-5
    ↓
Display to User
    ├─ Keywords (highlighted)
    ├─ Inconsistency Score
    ├─ Timestamp
    └─ Web references
```

## 🚀 How to Use

### 1. Set API Keys

Create/update `.env` file in root directory:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly_xxxxxxxxxxxxxxxxxxxxx
```

### 2. Start Django Server
```bash
python manage.py runserver
```

### 3. Login & Access Chatbot
- Visit: `http://127.0.0.1:8000/login/`
- Login as citizen: `citizen@example.com` / `Citizen@1234`
- Click "Complaint Assistant" or go to `/chatbot/`

### 4. Chat About a Problem
- Enter complaint in Bangla or English
- LLM extracts details
- Sidebar shows extracted keywords + inconsistency score
- Can file formal complaint when done

## 📊 Features

### Chat Session Storage
- All messages stored in Django DB
- Can view chat history
- Can continue incomplete chats

### Multi-language Support
- Bangla + English
- Groq LLM supports both
- Policy docs in Bangla
- System prompts adapted per language

### Keyword Extraction
- Real-time extraction after 3+ exchanges
- Shows: Category, Area, Duration, Keywords, Inconsistency, Timestamp

### Inconsistency Scoring
- 1 = Fully consistent with policy
- 3 = Mixed (some inconsistencies)
- 5 = Major inconsistencies found
- Based on: policy comparison + web search + extracted data

### Web Search Validation
- Tavily searches for similar complaints
- Finds real-world reports
- Validates if issue is widespread
- Flags if area/category unusual

## 🗂️ Database Models

```python
ChatSession
  ├─ user (FK)
  ├─ title
  ├─ language (en/bn)
  ├─ is_active
  └─ created_at, updated_at

ChatMessage
  ├─ chat_session (FK)
  ├─ role (user/assistant)
  ├─ content
  └─ timestamp

ExtractedComplaint
  ├─ chat_session (OneToOne)
  ├─ category
  ├─ area_thana
  ├─ duration
  ├─ keywords (JSON)
  ├─ inconsistency_score (1-5)
  ├─ web_search_results (JSON)
  └─ full_description
```

## 🔧 Troubleshooting

### "GROQ_API_KEY not found"
- Check `.env` file exists
- Verify key is correct
- Reload Django server

### "TAVILY_API_KEY not found"
- Same as above
- If you don't have Tavily API, web search will gracefully skip

### Chat not loading
- Check browser console for errors
- Verify Django server is running
- Check logs: `python manage.py runserver`

### Inconsistency score always 3
- Need more message history (min 3 exchanges)
- Web search might not have results
- Policy documents might need updating

## 📝 Next Steps

1. ✅ Set API keys in `.env`
2. ✅ Run migrations (already done)
3. ✅ Start server
4. ✅ Test chatbot
5. [ ] Update Bangla policy documents if needed
6. [ ] Customize complaint categories
7. [ ] Add email notifications when complaint filed
8. [ ] Deploy to production

## 🎯 Example Complaint Flow

```
User: "তিন মাস ধরে আমাদের রাস্তায় বড় গর্ত রয়েছে। মিরপুরে।"
(Translation: "We have a big pothole on our road for three months. In Mirpur.")

LLM Response:
"Thank you for reporting. I understand you have a pothole in Mirpur for 3 months. 
Can you tell me the exact location or road name?"

Extracted Data:
{
  "category": "road_damage/pothole",
  "area": "Mirpur",
  "duration": "3 months",
  "inconsistency_score": 2,  // Consistent - common issue
  "keywords": ["pothole", "road", "Mirpur", "3 months"]
}

Policy Reference:
"Road Maintenance Policy states potholes should be repaired within 24-48 hours"

Web Search:
"Found 12 reports of pothole issues in Mirpur area. Confirmed as ongoing problem."

User sees:
- Keywords highlighted
- Inconsistency score: 2/5 (mostly consistent)
- Can now file formal complaint
```

## 📖 API Endpoints

- `POST /chatbot/session/create/` - Create new chat session
- `POST /chatbot/session/<id>/message/` - Send message & get response
- `GET /chatbot/session/<id>/` - Load chat history
- `POST /chatbot/session/<id>/close/` - Close chat & save complaint

---

**Need help?** Check the Django admin at `/admin/` to view chat sessions and extracted data.
