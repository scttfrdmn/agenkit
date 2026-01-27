class CodeClient {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8000/ws');
        this.messages = document.getElementById('messages');
        this.currentMsg = '';
        this.currentEl = null;
        
        this.ws.onopen = () => console.log('Connected');
        this.ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            if (msg.event_type === 'text_message_chunk') {
                if (!this.currentEl) {
                    this.currentEl = document.createElement('div');
                    this.currentEl.className = 'message agent';
                    this.currentEl.innerHTML = '<div class="message-content"></div>';
                    this.messages.appendChild(this.currentEl);
                }
                this.currentMsg += msg.content;
                this.currentEl.querySelector('.message-content').textContent = this.currentMsg;
                this.messages.scrollTop = this.messages.scrollHeight;
            } else if (msg.event_type === 'text_message_complete') {
                this.currentMsg = '';
                this.currentEl = null;
            }
        };
    }
    
    send(text) {
        const input = document.getElementById('input');
        const content = text || input.value.trim();
        if (!content) return;
        
        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        userMsg.innerHTML = `<div class="message-content">${content}</div>`;
        this.messages.appendChild(userMsg);
        this.messages.scrollTop = this.messages.scrollHeight;
        
        this.ws.send(JSON.stringify({type: 'message', message: content}));
        input.value = '';
    }
}

let client;
window.addEventListener('DOMContentLoaded', () => {
    client = new CodeClient();
});

function send(text) {
    if (client) client.send(text);
}
