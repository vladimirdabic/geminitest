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
    Spinner, 
    Modal
} from 'react-bootstrap';
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

// KaTeX CSS
import "katex/dist/katex.min.css";

const api = import.meta.env.VITE_BACKEND_URL;
type Sender = "user" | "recipient";

interface JudgeResponse {
    verdict: string;
    score: number;
    overall_feedback: string;
    recommended_changes: string;
}

interface Message {
    text: string;
    sender: Sender;
    judge_data?: JudgeResponse;
}

interface ModalData {
    shown: boolean;
    title?: string;
    body?: React.ReactNode;
}

function App() {
    const [waiting, setWaiting] = useState(false);
    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const chatEndRef = useRef<HTMLDivElement | null>(null);
    const [modalData, setModalData] = useState<ModalData>({shown: false});

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
        setMessages(prev => [...prev, {text: prompt, sender: "user"}]);
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
            setMessages(prev => [...prev, {text: data["message"], sender: "recipient", judge_data: data["judge_data"]}])
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
                                       {(msg.sender == "recipient") && 
                                        <Button 
                                            variant="outline-secondary"
                                            onClick={(_) => setModalData({
                                                shown: true,
                                                title: "Dodatne informacije",
                                                body: <>
                                                    <p><strong>VERDICT</strong>: {msg.judge_data?.verdict}</p>
                                                    <p><strong>SCORE</strong>: {msg.judge_data?.score}/10</p>
                                                    <p><strong>FEEDBACK</strong>: {msg.judge_data?.overall_feedback}</p>
                                                    <p><strong>CHANGES</strong>: {msg.judge_data?.recommended_changes}</p>
                                                </>
                                            })}
                                        >?</Button>
                                       }
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

            <Modal
                show={modalData.shown}
                onHide={() => setModalData({shown: false})}
                backdrop="static"
                keyboard={false}
            >
                <Modal.Header closeButton>
                    <Modal.Title>{modalData.title}</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {modalData.body}
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setModalData({shown: false})}>
                        Close
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    )
}

export default App
