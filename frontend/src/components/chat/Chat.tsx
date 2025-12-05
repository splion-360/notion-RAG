import { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Stack,
  Tabs,
  Tab,
  Card,
  CardContent,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import toast from 'react-hot-toast';

const backendUrl = import.meta.env.VITE_WS_URL || 'http://127.0.0.1:8000';
const wsUrl = backendUrl.replace(/^http/, 'ws');

interface Message {
  role: 'user' | 'assistant';
  content: string;
  messageId?: string;
}

interface Chunk {
  page_title: string;
  chunk_content: string;
  similarity_score: number;
  page_id: string;
}

interface ChatProps {
  userId: string;
}

const markdownStyles = {
  '& p': { margin: '0 0 8px 0' },
  '& p:last-of-type': { marginBottom: 0 },
  '& ul, & ol': { margin: '0 0 8px 20px', padding: 0 },
  '& code': {
    fontFamily: 'monospace',
    backgroundColor: 'action.hover',
    borderRadius: '4px',
    padding: '0.15em 0.35em',
    fontSize: '0.95em',
  },
  '& pre': {
    fontFamily: 'monospace',
    backgroundColor: 'action.hover',
    borderRadius: '8px',
    padding: 1,
    overflowX: 'auto',
  },
  '& h1, & h2, & h3, & h4, & h5, & h6': {
    margin: '12px 0 8px',
  },
  '& hr': {
    border: 'none',
    borderTop: '1px solid',
    borderColor: 'divider',
    margin: '12px 0',
  },
};

function MarkdownContent({ content }: { content: string }) {
  return (
    <Box sx={{ ...markdownStyles }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || ''}
      </ReactMarkdown>
    </Box>
  );
}

export default function Chat({ userId }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [selectedChunks, setSelectedChunks] = useState<Chunk[]>([]);
  const [selectedPageContent, setSelectedPageContent] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMessageRef = useRef<string>('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const ws = new WebSocket(`${wsUrl}/api/v1/chat/ws?user_id=${userId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      toast.success('Connected to chat');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong' }));
          break;

        case 'conversation_id':
          setConversationId(data.data);
          break;

        case 'stream_start':
          setCurrentMessageId(data.message_id);
          setIsStreaming(true);
          streamingMessageRef.current = '';
          setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
          break;

        case 'chunks':
          setSelectedChunks(data.data || []);
          break;

        case 'stream':
          streamingMessageRef.current += data.content;
          setMessages((prev) => {
            const newMessages = [...prev];
            if (newMessages[newMessages.length - 1]?.role === 'assistant') {
              newMessages[newMessages.length - 1].content = streamingMessageRef.current;
            }
            return newMessages;
          });
          break;

        case 'complete':
          setIsStreaming(false);
          setCurrentMessageId(null);
          break;

        case 'generation_stopped':
          setIsStreaming(false);
          setCurrentMessageId(null);
          toast('Generation stopped', { icon: '⏸️' });
          break;

        case 'error':
          toast.error(data.message || 'An error occurred');
          setIsStreaming(false);
          break;

        case 'idle_timeout':
          toast.error('Connection timed out due to inactivity');
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      toast.error('Connection error');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      toast.error('Disconnected from chat');
    };

    wsRef.current = ws;

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [userId]);

  const handleSend = () => {
    if (!input.trim() || !isConnected || isStreaming) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInput('');

    wsRef.current?.send(
      JSON.stringify({
        type: 'chat',
        message: userMessage,
        conversation_id: conversationId,
      })
    );
  };

  const handleStop = () => {
    if (currentMessageId && wsRef.current) {
      wsRef.current.send(
        JSON.stringify({
          type: 'stop_generation',
          message_id: currentMessageId,
        })
      );
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleViewPage = async (pageId: string) => {
    try {
      const response = await fetch(`${backendUrl}/api/v1/notion/pages/${pageId}`);
      if (!response.ok) throw new Error('Failed to fetch page');

      const page = await response.json();
      setSelectedPageContent(page.content || 'No content available');
      setCurrentTab(2);
    } catch (error) {
      toast.error('Failed to load page content');
      console.error(error);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 100px)', gap: 2 }}>
      <Box sx={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Chat with your Notion
        </Typography>

        <Paper
          sx={{
            flex: 1,
            p: 2,
            mb: 2,
            overflow: 'auto',
            bgcolor: 'background.default',
          }}
        >
          <Stack spacing={2}>
            {messages.map((msg, idx) => (
              <Box
                key={idx}
                sx={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <Paper
                  sx={{
                    p: 2,
                    maxWidth: '70%',
                    bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                    color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                  }}
                >
                  <MarkdownContent content={msg.content} />
                </Paper>
              </Box>
            ))}
            <div ref={messagesEndRef} />
          </Stack>
        </Paper>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your Notion pages..."
            disabled={!isConnected || isStreaming}
          />
          {isStreaming ? (
            <IconButton onClick={handleStop} color="error">
              <StopIcon />
            </IconButton>
          ) : (
            <IconButton
              onClick={handleSend}
              disabled={!input.trim() || !isConnected}
              color="primary"
            >
              <SendIcon />
            </IconButton>
          )}
        </Box>

        {!isConnected && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="caption" color="text.secondary">
              Connecting to chat...
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Tabs value={currentTab} onChange={(_, val) => setCurrentTab(val)}>
          <Tab label="Chunks" />
          <Tab label="Page" />
        </Tabs>

        <Paper sx={{ flex: 1, mt: 2, p: 2, overflow: 'auto' }}>
          {currentTab === 0 && (
            <Stack spacing={2}>
              {selectedChunks.length > 0 ? (
                selectedChunks.map((chunk, idx) => (
                  <Card key={idx} variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2">{chunk.page_title}</Typography>
                        <Chip
                          label={`${(chunk.similarity_score * 100).toFixed(1)}%`}
                          size="small"
                          color="primary"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {chunk.chunk_content}
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        <Typography
                          variant="caption"
                          color="primary"
                          sx={{ cursor: 'pointer', textDecoration: 'underline' }}
                          onClick={() => handleViewPage(chunk.page_id)}
                        >
                          View full page →
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <Typography variant="body2" color="text.secondary" align="center">
                  No chunks retrieved yet. Ask a question to see relevant sources.
                </Typography>
              )}
            </Stack>
          )}

          {currentTab === 1 && (
            <Box>
              {selectedPageContent ? (
                <MarkdownContent content={selectedPageContent} />
              ) : (
                <Typography variant="body2" color="text.secondary" align="center">
                  Click "View full page" on a chunk to see the complete page content.
                </Typography>
              )}
            </Box>
          )}
        </Paper>
      </Box>
    </Box>
  );
}
