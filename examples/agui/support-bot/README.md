# Customer Support Bot

Production-ready example demonstrating context-aware customer support with ticket tracking and escalation through AG-UI protocol.

## 🎯 Overview

This example showcases an intelligent support bot that maintains conversation history, tracks tickets, classifies issues, and escalates to human agents when needed.

### Key Features

- ✅ **Context Tracking**: Maintains full conversation history
- ✅ **Ticket Management**: Auto-creates and tracks support tickets
- ✅ **Issue Classification**: Categorizes issues (technical, billing, inquiry)
- ✅ **Knowledge Base**: Provides instant solutions for common issues
- ✅ **Smart Escalation**: Routes complex issues to human agents
- ✅ **Priority System**: HIGH/MEDIUM/LOW priority handling
- ✅ **Production Ready**: Full ticket lifecycle management

## 🚀 Quick Start

```bash
docker-compose up --build
open http://localhost:3000
```

## 🎮 Usage

### Common Issues (Quick Buttons)

- **🔐 Login Issue** → Knowledge base solution + password reset
- **💳 Billing** → Escalates to billing specialist (high priority)
- **⏱️ Performance** → Troubleshooting steps
- **🐛 Bug Report** → Creates bug ticket for engineering
- **👤 Human Agent** → Immediate escalation

### Example Conversations

**Login Issue (Auto-resolved)**:
```
User: I cannot login to my account
Bot: [Solution with password reset link + cache clearing steps]
Bot: Did this resolve your issue?
```

**Billing Question (Auto-escalated)**:
```
User: I have a billing question
Bot: I'm escalating your case to a billing specialist
Bot: Ticket ID: abc12345 | Priority: HIGH
Bot: Average response time: 15-30 minutes
```

**Extended Conversation (Auto-escalated after 10+ messages)**:
```
[After 11 messages without resolution]
Bot: I'm escalating to a human support agent who can better assist you
```

## 📊 Ticket Lifecycle

1. **Created**: User sends first message
2. **Classified**: Issue type and priority determined
3. **Solution Provided**: Knowledge base or custom response
4. **Escalated** (if needed): Routed to human agent
5. **Resolved**: Issue marked complete

## 🔧 Configuration

### Add Knowledge Base Entry

Edit `backend/agent.py`:
```python
self._knowledge_base["new_issue"] = {
    "solution": "Your solution here...",
    "priority": "medium",
    "category": "technical",
}
```

### Modify Escalation Logic

```python
def _should_escalate(self, content, ticket, classification):
    # Custom escalation rules
    if "vip_customer" in ticket.metadata:
        return True
    return False
```

## 📖 API Reference

### GET /tickets
List all support tickets

### GET /tickets/{ticket_id}
Get ticket details with full conversation history

### GET /statistics
Support metrics: total, open, resolved, escalation rate

## 🐛 Troubleshooting

### Ticket Not Creating
- Verify customer_id in message metadata
- Check backend logs for errors

### Escalation Not Working
- Review `_should_escalate()` logic
- Check escalation keywords

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

---

**Built with ❤️ using Agenkit**
