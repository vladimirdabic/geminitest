import { useState, useRef, useEffect } from "react";
import "./App.css"
import { 
    Container,
    Button,
    Row,
    Col,
    Stack,
    Form,
    Toast,
    Spinner 
} from 'react-bootstrap';
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

// KaTeX CSS
import "katex/dist/katex.min.css";

const api = import.meta.env.VITE_BACKEND_URL;
type Sender = "user" | "recipient";

class Message {
    public text: string;
    public sender: Sender;

    public constructor(text: string, sender: Sender) {
        this.text = text;
        this.sender = sender;
    }
}

function App() {
    const [waiting, setWaiting] = useState(false);
    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const chatEndRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if(chatEndRef.current) {
            chatEndRef.current.scrollTo({
                top: chatEndRef.current.scrollHeight,
                behavior: "smooth"
            });
        }
    }, [messages]);

    const sendMessage = function() {
        if (prompt.trim() === "") return;
        setMessages(prev => [...prev, new Message(prompt, "user")]);
        setPrompt("");

        setWaiting(true);
        
        fetch(`${api}/prompt`, {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: prompt.trim()
            }),
            credentials: "include"
        })
        .then(resp => resp.json())
        .then(data => {
            setMessages(prev => [...prev, new Message(data["message"], "recipient")])
            setWaiting(false);
        })
    }

    return (
        <>
            <Container fluid className="history" ref={chatEndRef}>
                <Row className="justify-content-center">
                    <Col className="d-flex flex-column">
                        <Stack gap={2}>
                            {messages.map((msg, i) => <div
                                key={i}
                                className={`d-flex ${msg.sender === "user" ? "justify-content-end" : "justify-content-start"}`}
                            >
                                <Toast className="message">
                                    <Toast.Header closeButton={false}>
                                       <strong className='me-auto'>{msg.sender === "user" ? "You" : "Response"}</strong>
                                    </Toast.Header>
                                    <Toast.Body>
                                        <Markdown
                                            remarkPlugins={[remarkMath]}
                                            rehypePlugins={[rehypeKatex]}
                                        >
                                            {msg.text}
                                        </Markdown>
                                    </Toast.Body>
                                </Toast>
                            </div>)}
                        </Stack>
                    </Col>
                </Row>
            </Container>
            <Container>
                <Row className="justify-content-center py-3">
                    <Col md={15}>
                            <Form>
                            <Row>
                                <Col>
                                    <Form.Control 
                                        placeholder='Pozdrav'
                                        onChange={(e) => setPrompt(e.target.value)}
                                        onKeyDown={(e) => {
                                            if(e.key == "Enter" && !e.shiftKey) {
                                                e.preventDefault();
                                                sendMessage();
                                            }
                                        }}
                                        value={prompt}
                                        disabled={waiting}
                                    /> 
                                </Col>
                                <Col xs="auto" className="d-flex align-items-stretch">
                                    <Button variant='primary' onClick={sendMessage} disabled={waiting}>Submit</Button>
                                    {waiting && <Spinner animation="border" role="status">
                                        <span className="visually-hidden">Loading...</span>
                                    </Spinner>}
                                </Col>
                            </Row>
                        </Form>
                    </Col>
                </Row>
            </Container>
        </>
    )
}

export default App
