import { useState, useCallback } from 'react';
import axios from 'axios';
import LevelSelector from './components/LevelSelector';
import TopicSidebar from './components/TopicSidebar';
import ChatWindow from './components/ChatWindow';
import './App.css';

function generateUserId() {
  return 'user_' + Math.random().toString(36).slice(2, 11);
}

const TOPIC_STARTERS = {
  '技术': '我想了解网球技术，可以从哪里开始？',
  '战术': '能给我讲讲网球比赛中的战术策略吗？',
  '训练': '如何制定适合我水平的训练计划？',
  '装备': '我应该如何选择适合自己的球拍？',
  '其他': '我有一个关于网球的问题想请教你。',
};

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: '你好！我是你的 AI 网球教练，拥有 20 年执教经验。\n\n你可以问我任何关于**网球技术**、**战术策略**、**训练计划**或**装备选择**的问题。左侧选择话题分类可以快速开始，或者直接输入你的问题！\n\n你目前遇到什么网球难题？',
  isUncertain: false,
};

export default function App() {
  const [userId] = useState(() => {
    const stored = localStorage.getItem('tennis_user_id');
    if (stored) return stored;
    const id = generateUserId();
    localStorage.setItem('tennis_user_id', id);
    return id;
  });

  const [userLevel, setUserLevel] = useState(() =>
    localStorage.getItem('tennis_user_level') || null
  );
  const [showLevelSelector, setShowLevelSelector] = useState(
    !localStorage.getItem('tennis_user_level')
  );
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTopic, setActiveTopic] = useState(null);

  const handleLevelSelect = (level) => {
    setUserLevel(level);
    if (level) {
      localStorage.setItem('tennis_user_level', level);
    } else {
      localStorage.removeItem('tennis_user_level');
    }
    setShowLevelSelector(false);
  };

  const sendMessage = useCallback(async (messageText) => {
    const userMsg = { role: 'user', content: messageText };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const { data } = await axios.post('/chat', {
        message: messageText,
        user_id: userId,
        user_level: userLevel || undefined,
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply,
        isUncertain: data.is_uncertain,
        sources: data.sources,
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '抱歉，我现在遇到了一些技术问题，请稍后再试。',
        isUncertain: false,
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [userId, userLevel]);

  const handleTopicSelect = (topic) => {
    setActiveTopic(topic);
    const starter = TOPIC_STARTERS[topic];
    if (starter) sendMessage(starter);
  };

  if (showLevelSelector) {
    return <LevelSelector onSelect={handleLevelSelect} />;
  }

  return (
    <div className="app-container">
      <TopicSidebar
        activeTopic={activeTopic}
        onTopicSelect={handleTopicSelect}
        userLevel={userLevel}
        onChangeLevel={() => setShowLevelSelector(true)}
      />
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSendMessage={sendMessage}
      />
    </div>
  );
}
